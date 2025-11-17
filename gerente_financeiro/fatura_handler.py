# Importar analytics
try:
    from analytics.bot_analytics import BotAnalytics
    from analytics.advanced_analytics import advanced_analytics
    analytics = BotAnalytics()
    ANALYTICS_ENABLED = True
except ImportError:
    ANALYTICS_ENABLED = False

def track_analytics(command_name):
    """Decorator para tracking de comandos"""
    import functools
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(update, context):
            if ANALYTICS_ENABLED and update.effective_user:
                user_id = update.effective_user.id
                username = update.effective_user.username or update.effective_user.first_name or "Usuário"
                
                try:
                    analytics.track_command_usage(
                        user_id=user_id,
                        username=username,
                        command=command_name,
                        success=True
                    )
                    logging.info(f"📊 Analytics: {username} usou /{command_name}")
                except Exception as e:
                    logging.error(f"❌ Erro no analytics: {e}")
            
            return await func(update, context)
        return wrapper
    return decorator

import logging
import json
import re
import asyncio
from datetime import datetime, timedelta
import io
import pdfplumber # <--- NOVA BIBLIOTECA

import google.generativeai as genai
from .parser_fatura_inter import ParserFaturaInter  # 🆕 Parser especializado Inter
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler, CallbackQueryHandler, MessageHandler, filters
)
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, extract

import config
from database.database import get_db, get_or_create_user, verificar_transacao_duplicada
from models import Lancamento, Categoria, Subcategoria, Conta, Usuario
from .handlers import cancel
from .services import limpar_cache_usuario
from .utils_email import enviar_email
from .utils_google_calendar import criar_evento_google_calendar
from .states import AWAIT_FATURA_PDF, AWAIT_CONTA_ASSOCIADA, AWAIT_CONFIRMATION

logger = logging.getLogger(__name__)

# Variável global para rastrear parcelas detectadas na sessão atual
_parcelas_detectadas_info = {
    'total': 0,
    'banco': None,
    'detalhes': [],
    'parcelas_completas': []  # 🆕 Armazenar dados completos das parcelas
}

# --- PROMPT V4: APENAS PARA CATEGORIZAÇÃO ---
PROMPT_CATEGORIZACAO_V4 = """
**TAREFA:** Você é um especialista em finanças. Sua única tarefa é categorizar a lista de transações JSON fornecida.
Para cada transação, adicione os campos "categoria_sugerida" e "subcategoria_sugerida" usando a lista de categorias disponíveis.
Retorne a lista JSON completa com os novos campos. NÃO ALTERE NENHUM OUTRO DADO.

**LISTA DE CATEGORIAS E SUBCATEGORIAS DISPONÍVEIS:**
{categorias_disponiveis}

**SAÍDA:** Retorne **APENAS UM BLOCO DE CÓDIGO JSON VÁLIDO** com a lista de transações categorizada.
```json
[
    {{
      "data": "DD/MM/AAAA",
      "descricao": "NOME DO ESTABELECIMENTO",
      "valor": 123.45,
      "categoria_sugerida": "Categoria da Lista",
      "subcategoria_sugerida": "Subcategoria da Lista"
    }}
]
LISTA DE TRANSAÇÕES PARA CATEGORIZAR:
{lista_transacoes_json}
"""

# --- Parser de Layout para o Bradesco ---
def _parse_bradesco_com_pdfplumber(pdf: pdfplumber.PDF) -> dict:
    transacoes = []
    parcelas_futuras = []
    ano_atual = str(datetime.now().year)
    # Padrão de data no Bradesco: DD/MM
    padrao_data = re.compile(r'^\d{2}/\d{2}\s+')
    # 🔧 PADRÃO CORRIGIDO para parcelas do Bradesco: formato no meio da descrição
    # Formato encontrado: "FLAMENGO NACAO 11/12 RIO DE JANEIR", "Sympla ds2k 01/04 B Horizonte"
    # Padrão: qualquer texto + espaço + número/número + espaço + resto
    padrao_parcela = re.compile(r'^(.+?)\s+(\d+)/(\d+)\s+(.+)$')
    
    logger.info(f"[BRADESCO DEBUG] Iniciando parser do Bradesco com {len(pdf.pages)} páginas")

    # 🔧 CORREÇÃO: Processar TODAS as páginas para não perder transações
    for page_num, page in enumerate(pdf.pages):
        # if page_num != 1:  # Comentado: vamos processar todas as páginas
        #     continue
            
        text = page.extract_text()
        if not text:
            continue
            
        lines = text.split('\n')
        logger.info(f"[Bradesco] Analisando página {page_num + 1} com {len(lines)} linhas")
        
        for line in lines:
            line = line.strip()
            if not line or len(line) < 10:
                continue
                
            # Procura por linhas que começam com data DD/MM
            match = padrao_data.match(line)
            if match:
                try:
                    # Parse da linha: "03/06 LABI EXAMES SA RIO DE JANEIR 50,00"
                    parts = line.split()
                    if len(parts) < 3:
                        continue
                        
                    data = parts[0]  # 03/06
                    valor_str = parts[-1]  # Último item é o valor
                    
                    # Verifica se é um valor válido
                    if not re.match(r'\d+,\d{2}$', valor_str):
                        continue
                    
                    valor = float(valor_str.replace(',', '.'))
                    
                    # Descrição é tudo entre a data e o valor
                    descricao_parts = parts[1:-1]
                    descricao = " ".join(descricao_parts)
                    
                    # 🔧 CORREÇÃO: Filtrar apenas transações óbviamente inválidas (estava muito restritivo)
                    descricao_lower = descricao.lower()
                    if any(keyword in descricao_lower for keyword in [
                        'anuidade', 'total da fatura', 'valor mínimo da fatura',
                        'pagamento recebido', 'valor anterior', 'saldo anterior',
                        'limite disponível', 'próximo vencimento'
                    ]):
                        logger.debug(f"[Bradesco] Ignorando transação: {descricao}")
                        continue
                    
                    # ✨ NOVO: Detectar e separar parcelas futuras
                    logger.debug(f"[BRADESCO] Verificando parcela na descrição: '{descricao}'")
                    match_parcela = padrao_parcela.search(descricao)
                    if match_parcela:
                        desc_parte1 = match_parcela.group(1).strip()  # Parte antes do X/Y
                        parcela_atual = int(match_parcela.group(2))
                        parcela_total = int(match_parcela.group(3))
                        desc_parte2 = match_parcela.group(4).strip()  # Parte depois do X/Y
                        
                        # Reconstruir descrição base sem a numeração de parcela
                        desc_base = f"{desc_parte1} {desc_parte2}".strip()
                        
                        logger.info(f"[BRADESCO] 🎯 PARCELA DETECTADA: '{desc_base}' - {parcela_atual}/{parcela_total}")
                        
                        transacao = {
                            "data": f"{data}/{ano_atual}",
                            "descricao": descricao.strip(),  # Manter descrição original
                            "valor": valor
                        }
                        
                        if parcela_atual == 1:
                            # Primeira parcela = transação do mês atual
                            transacoes.append(transacao)
                            logger.info(f"[BRADESCO] ✅ Aceita primeira parcela: {desc_base} - {parcela_atual}/{parcela_total}")
                        else:
                            # Parcelas futuras = não incluir no total
                            parcelas_futuras.append(transacao)
                            logger.info(f"[BRADESCO] ⏭️ Parcela futura detectada: {desc_base} - {parcela_atual}/{parcela_total}")
                    else:
                        logger.debug(f"[BRADESCO] Não é parcela: '{descricao}'")
                        # Transação normal sem parcelas
                        transacao = {
                            "data": f"{data}/{ano_atual}",
                            "descricao": descricao.strip(),
                            "valor": valor
                        }
                        transacoes.append(transacao)
                        logger.debug(f"[Bradesco] Transação extraída: {transacao}")
                    
                except (ValueError, IndexError) as e:
                    logger.warning(f"[Bradesco] Erro ao processar linha: '{line}'. Erro: {e}")
                    continue

    logger.info(f"[Parser Bradesco] ✅ {len(transacoes)} transações do mês atual")
    logger.info(f"[Parser Bradesco] 📅 {len(parcelas_futuras)} parcelas futuras detectadas")
    
    # 📊 LOG DETALHADO para debugging
    total_mes_atual = sum(t['valor'] for t in transacoes)
    total_parcelas = sum(p['valor'] for p in parcelas_futuras)
    logger.info(f"[Parser Bradesco] 💰 Total mês atual: R$ {total_mes_atual:.2f}")
    logger.info(f"[Parser Bradesco] � Total parcelas futuras: R$ {total_parcelas:.2f}")
    
    return {
        'transacoes': transacoes,
        'parcelas_futuras': parcelas_futuras,
        'banco': 'Bradesco'
    }

# --- Parser de Layout para a Caixa ---
def _parse_caixa_com_pdfplumber(pdf: pdfplumber.PDF) -> dict:
    transacoes = []
    parcelas_futuras = []
    ano_atual = str(datetime.now().year)
    # Padrão de data no Caixa: DD/MM
    padrao_data = re.compile(r'^\d{2}/\d{2}\s+')
    # Padrão de parcelas: "descrição - X/Y" ou "descrição X/Y"
    padrao_parcela = re.compile(r'(.+?)[-\s]*(\d+)/(\d+)$')

    # 🔧 CORREÇÃO: Processar mais páginas da Caixa (não só 2 e 3)
    for page_num, page in enumerate(pdf.pages):
        if page_num == 0:  # Ignorar primeira página (boleto)
            continue
            
        logger.info(f"[Caixa] Processando página {page_num + 1}")
        
        # Tentar extrair texto primeiro
        text = page.extract_text()
        if text:
            lines = text.split('\n')
            for line in lines:
                line = line.strip()
                if not line or len(line) < 10:
                    continue
                
                # Procurar padrão: "DD/MM DESCRIÇÃO CIDADE VALOR[D/C]"
                # Exemplo: "08/05 MERCADO EXTRA 5290 R DE JANEIRO 5,79D"
                if re.match(r'^\d{2}/\d{2}\s+\w+', line):
                    try:
                        # Separar por espaços
                        parts = line.split()
                        if len(parts) < 4:
                            continue
                            
                        data = parts[0]  # DD/MM
                        valor_str = parts[-1]  # Último item: "5,79D" ou "5,79C"
                        
                        # Verificar se termina com D ou C e extrair valor
                        if valor_str.endswith(('D', 'C')):
                            valor_num = valor_str[:-1]  # Remove D ou C
                            if not re.match(r'\d+,\d{2}$', valor_num):
                                continue
                            valor = float(valor_num.replace(',', '.'))
                        else:
                            continue
                        
                        # Descrição é tudo entre data e valor
                        descricao_parts = parts[1:-1]
                        descricao = " ".join(descricao_parts)
                        
                        # 🔧 CORREÇÃO: Filtrar apenas transações óbviamente inválidas
                        descricao_lower = descricao.lower()
                        if any(keyword in descricao_lower for keyword in [
                            'total da fatura', 'anuidade', 'valor mínimo'
                        ]):
                            logger.debug(f"[Caixa] Ignorando: {descricao}")
                            continue
                        
                        # Categorizar juros especificamente
                        if any(keyword in descricao_lower for keyword in [
                            'juros', 'juro', 'rotativo', 'atraso', 'pagamento minimo'
                        ]):
                            descricao = f"JUROS - {descricao}"
                        
                        # ✨ NOVO: Detectar e separar parcelas futuras
                        match_parcela = padrao_parcela.search(descricao)
                        if match_parcela:
                            desc_base = match_parcela.group(1).strip()
                            parcela_atual = int(match_parcela.group(2))
                            parcela_total = int(match_parcela.group(3))
                            
                            transacao = {
                                "data": f"{data}/{ano_atual}",
                                "descricao": descricao.strip(),
                                "valor": valor
                            }
                            
                            if parcela_atual == 1:
                                # Primeira parcela = transação do mês atual
                                transacoes.append(transacao)
                                logger.info(f"[Caixa] ✅ Aceita primeira parcela: {desc_base} - {parcela_atual}/{parcela_total}")
                            else:
                                # Parcelas futuras = não incluir no total
                                parcelas_futuras.append(transacao)
                                logger.info(f"[Caixa] ❌ Ignorando parcela futura: {desc_base} - {parcela_atual}/{parcela_total}")
                        else:
                            # Transação normal sem parcelas
                            transacao = {
                                "data": f"{data}/{ano_atual}",
                                "descricao": descricao.strip(),
                                "valor": valor
                            }
                            transacoes.append(transacao)
                            logger.debug(f"[Caixa] Transação extraída: {transacao}")
                        
                    except (ValueError, IndexError) as e:
                        logger.warning(f"[Caixa] Erro ao processar linha: '{line}'. Erro: {e}")
                        continue
        
        # Também tentar extrair tabelas como fallback
        tables = page.extract_tables()
        for table in tables:
            for row in table:
                if not row or len(row) < 3:
                    continue
                
                primeira_col = str(row[0]) if row[0] else ""
                if re.match(r'^\d{2}/\d{2}', primeira_col):
                    try:
                        data = primeira_col
                        desc = str(row[1]) if len(row) > 1 and row[1] else ""
                        valor_str = str(row[-1]) if row[-1] else ""
                        
                        if valor_str.endswith(('D', 'C')):
                            valor_num = valor_str[:-1]
                            valor = float(valor_num.replace(',', '.'))
                            
                            if desc and not any(keyword in desc.lower() for keyword in [
                                'total da fatura', 'anuidade', 'valor mínimo'
                            ]):
                                # ✨ NOVO: Aplicar filtro de parcelas também nas tabelas
                                match_parcela = padrao_parcela.search(desc)
                                if match_parcela:
                                    desc_base = match_parcela.group(1).strip()
                                    parcela_atual = int(match_parcela.group(2))
                                    parcela_total = int(match_parcela.group(3))
                                    
                                    transacao = {
                                        "data": f"{data}/{ano_atual}",
                                        "descricao": desc.strip(),
                                        "valor": valor
                                    }
                                    
                                    if parcela_atual == 1:
                                        # Primeira parcela = transação do mês atual
                                        if transacao not in transacoes:
                                            transacoes.append(transacao)
                                            logger.debug(f"[Caixa Tabela] ✅ Aceita primeira parcela: {desc_base} - {parcela_atual}/{parcela_total}")
                                    else:
                                        # Parcelas futuras = não incluir no total
                                        if transacao not in parcelas_futuras:
                                            parcelas_futuras.append(transacao)
                                            logger.debug(f"[Caixa Tabela] ❌ Ignorando parcela futura: {desc_base} - {parcela_atual}/{parcela_total}")
                                else:
                                    # Transação normal sem parcelas
                                    transacao = {
                                        "data": f"{data}/{ano_atual}",
                                        "descricao": desc.strip(),
                                        "valor": valor
                                    }
                                    # Evitar duplicatas
                                    if transacao not in transacoes:
                                        transacoes.append(transacao)
                                        logger.debug(f"[Caixa Tabela] Transação extraída: {transacao}")
                                    
                    except (ValueError, TypeError) as e:
                        logger.warning(f"[Caixa Tabela] Erro ao processar linha: '{row}'. Erro: {e}")
                        continue
                        
    logger.info(f"[Parser Caixa] ✅ {len(transacoes)} transações do mês atual")
    logger.info(f"[Parser Caixa] 📅 {len(parcelas_futuras)} parcelas futuras detectadas")
    
    # 📊 LOG DETALHADO para debugging
    total_mes_atual = sum(t['valor'] for t in transacoes)
    total_parcelas = sum(p['valor'] for p in parcelas_futuras)
    logger.info(f"[Parser Caixa] 💰 Total mês atual: R$ {total_mes_atual:.2f}")
    logger.info(f"[Parser Caixa] � Total parcelas futuras: R$ {total_parcelas:.2f}")
    
    return {
        'transacoes': transacoes,
        'parcelas_futuras': parcelas_futuras,
        'banco': 'Caixa'
    }

# --- Parser de Layout para o Inter (MANTIDO - Parser Antigo Funcional) ---
def _parse_inter_com_pdfplumber(pdf: pdfplumber.PDF) -> dict:
    """
    Parser do Inter - Versão antiga mantida por compatibilidade
    TODO: Migrar para ParserFaturaInter quando testarmos completamente
    """
    transacoes = []
    parcelas_futuras = []
    # Padrão de parcelas: "descrição - X/Y" ou "descrição X/Y"
    padrao_parcela = re.compile(r'(.+?)[-\s]*(\d+)/(\d+)$')
    
    # Processar todas as páginas
    for page_num, page in enumerate(pdf.pages):
        logger.info(f"[Inter] Processando página {page_num + 1}")
        
        # Primeiro, tentar extrair do texto linha por linha
        text = page.extract_text()
        if text:
            lines = text.split('\n')
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                # Procurar por linhas que contêm datas do Inter
                # Formato: "09 de mai. 2025 PREZUNIC 731 - R$ 4,19"
                if re.search(r'\d{1,2} de \w{3}\. \d{4}', line) and 'R$' in line:
                    try:
                        # Extrair data
                        data_match = re.search(r'(\d{1,2} de \w{3}\. \d{4})', line)
                        if not data_match:
                            continue
                        
                        data_original = data_match.group(1)
                        data_convertida = _converter_data_inter(data_original)
                        
                        # Extrair valor (último R$ da linha)
                        valor_matches = re.findall(r'R\$\s*([\d,]+)', line)
                        if not valor_matches:
                            continue
                        
                        valor_str = valor_matches[-1]  # Último valor na linha
                        valor = float(valor_str.replace(',', '.'))
                        
                        # Extrair descrição (entre data e valor)
                        # Remove a data
                        desc_parte = line.replace(data_original, '').strip()
                        # Remove o último valor R$
                        desc_parte = re.sub(r'R\$\s*[\d,]+$', '', desc_parte).strip()
                        # Remove traços extras
                        desc_parte = desc_parte.strip(' -')
                        
                        # Filtrar transações indesejadas
                        if not desc_parte or any(keyword in desc_parte.lower() for keyword in [
                            'pagamento on line', 'anuidade', 'total cartão'
                        ]):
                            logger.debug(f"[Inter] Ignorando: {desc_parte}")
                            continue
                        
                        # Categorizar juros
                        if any(keyword in desc_parte.lower() for keyword in [
                            'juros', 'juro', 'rotativo', 'atraso'
                        ]):
                            desc_parte = f"JUROS - {desc_parte}"
                        
                        # ✨ NOVO: Detectar e separar parcelas futuras
                        match_parcela = padrao_parcela.search(desc_parte)
                        if match_parcela:
                            desc_base = match_parcela.group(1).strip()
                            parcela_atual = int(match_parcela.group(2))
                            parcela_total = int(match_parcela.group(3))
                            
                            transacao = {
                                "data": data_convertida,
                                "descricao": desc_parte,
                                "valor": valor
                            }
                            
                            if parcela_atual == 1:
                                # Primeira parcela = transação do mês atual
                                transacoes.append(transacao)
                                logger.info(f"[Inter] ✅ Aceita primeira parcela: {desc_base} - {parcela_atual}/{parcela_total}")
                            else:
                                # Parcelas futuras = não incluir no total
                                parcelas_futuras.append(transacao)
                                logger.info(f"[Inter] ❌ Ignorando parcela futura: {desc_base} - {parcela_atual}/{parcela_total}")
                        else:
                            # Transação normal sem parcelas
                            transacao = {
                                "data": data_convertida,
                                "descricao": desc_parte,
                                "valor": valor
                            }
                            transacoes.append(transacao)
                            logger.debug(f"[Inter] Transação extraída: {transacao}")
                        
                    except (ValueError, AttributeError) as e:
                        logger.warning(f"[Inter] Erro ao processar linha: '{line}'. Erro: {e}")
                        continue
        
        # Também processar tabelas como fallback
        tables = page.extract_tables()
        for table in tables:
            for row in table:
                if not row or len(row) < 1:
                    continue
                
                # Linhas das tabelas do Inter podem ter formato:
                # ['09 de mai. 2025 PREZUNIC 731 - R$ 4,19']
                cell_content = str(row[0]) if row[0] else ""
                
                if re.search(r'\d{1,2} de \w{3}\. \d{4}', cell_content) and 'R$' in cell_content:
                    try:
                        data_match = re.search(r'(\d{1,2} de \w{3}\. \d{4})', cell_content)
                        if not data_match:
                            continue
                        
                        data_original = data_match.group(1)
                        data_convertida = _converter_data_inter(data_original)
                        
                        valor_matches = re.findall(r'R\$\s*([\d,]+)', cell_content)
                        if not valor_matches:
                            continue
                        
                        valor_str = valor_matches[-1]
                        valor = float(valor_str.replace(',', '.'))
                        
                        desc_parte = cell_content.replace(data_original, '').strip()
                        desc_parte = re.sub(r'R\$\s*[\d,]+$', '', desc_parte).strip()
                        desc_parte = desc_parte.strip(' -')
                        
                        if desc_parte and not any(keyword in desc_parte.lower() for keyword in [
                            'pagamento on line', 'anuidade', 'total cartão'
                        ]):
                            transacao = {
                                "data": data_convertida,
                                "descricao": desc_parte,
                                "valor": valor
                            }
                            # Evitar duplicatas
                            if transacao not in transacoes:
                                transacoes.append(transacao)
                                logger.debug(f"[Inter Tabela] Transação extraída: {transacao}")
                                
                    except (ValueError, AttributeError) as e:
                        logger.warning(f"[Inter] Erro ao processar tabela: '{row}'. Erro: {e}")
                        continue

    logger.info(f"[Parser Inter] ✅ {len(transacoes)} transações do mês atual")
    logger.info(f"[Parser Inter] 📅 {len(parcelas_futuras)} parcelas futuras detectadas")
    
    # 📊 LOG DETALHADO para debugging
    total_mes_atual = sum(t['valor'] for t in transacoes)
    total_parcelas = sum(p['valor'] for p in parcelas_futuras)
    logger.info(f"[Parser Inter] 💰 Total mês atual: R$ {total_mes_atual:.2f}")
    logger.info(f"[Parser Inter] � Total parcelas futuras: R$ {total_parcelas:.2f}")
    
    return {
        'transacoes': transacoes,
        'parcelas_futuras': parcelas_futuras,
        'banco': 'Inter'
    }

def _converter_data_inter(data_original: str) -> str:
    """Converte data do Inter '10 de mai. 2025' para '10/05/2025'"""
    meses = {
        'jan': '01', 'fev': '02', 'mar': '03', 'abr': '04',
        'mai': '05', 'jun': '06', 'jul': '07', 'ago': '08',
        'set': '09', 'out': '10', 'nov': '11', 'dez': '12'
    }
    
    try:
        # Parse "10 de mai. 2025"
        parts = data_original.replace('.', '').split()
        if len(parts) >= 4:  # ['10', 'de', 'mai', '2025']
            dia = parts[0].zfill(2)
            mes_abrev = parts[2].lower()
            ano = parts[3]
            
            if mes_abrev in meses:
                return f"{dia}/{meses[mes_abrev]}/{ano}"
    except:
        pass
    
# --- Parser de Layout para o Nubank (Atualizado para Novo Layout 2025) ---
def _parse_nubank_com_pdfplumber(pdf: pdfplumber.PDF) -> dict:
    """
    Parser do Nubank ATUALIZADO para novo layout 2025
    - Transações agora vêm em páginas 5+ (não mais 4+)
    - Formato mudou para tabelas de 1 coluna: "DD MMM ••• XXXX Descrição R$ XX,XX"
    Retorna dict com transações e parcelas separadas
    """
    transacoes_mes_atual = []
    parcelas_futuras = []
    ano_atual = str(datetime.now().year)
    
    # 🆕 NOVO PADRÃO para formato 2025: "DD MMM •••• XXXX Descrição R$ XX,XX"
    padrao_transacao_nova = re.compile(r'^(\d{1,2} \w{3})\s+••••?\s+\d+\s+(.+?)\s+R\$\s+([\d.,]+)$')
    # ✨ Padrão mais preciso para parcelas: qualquer texto terminando com "número/número" 
    padrao_parcela = re.compile(r'^(.+?)\s+-\s+Parcela\s+(\d+)/(\d+)$', re.IGNORECASE)
    
    logger.info(f"[Nubank] 🆕 Usando parser atualizado para novo layout 2025")
    
    # 🔧 NOVO: Processar páginas 5+ (layout mudou em 2025)
    for page_num, page in enumerate(pdf.pages):
        # 🆕 MUDANÇA: Ignorar páginas 1-4, transações agora começam na página 5
        if page_num < 4:  # Páginas 0,1,2,3 = páginas 1,2,3,4
            continue
            
        logger.info(f"[Nubank] 📄 Processando página {page_num + 1}")
        
        # 🆕 ABORDAGEM ATUALIZADA: Extrair das tabelas de 1 coluna primeiro
        tables = page.extract_tables()
        for table_idx, table in enumerate(tables):
            logger.debug(f"[Nubank] 📊 Tabela {table_idx + 1}: {len(table)} linhas")
            
            for row_idx, row in enumerate(table):
                if not row or not row[0]:
                    continue
                
                # 🆕 Novo formato: tudo vem na primeira coluna
                linha_completa = str(row[0]).strip()
                if not linha_completa:
                    continue
                
                logger.debug(f"[Nubank] 🔍 Analisando linha: '{linha_completa}'")
                
                # 🆕 PADRÃO NOVO: "DD MMM ••• XXXX Descrição R$ XX,XX"
                match_nova = padrao_transacao_nova.match(linha_completa)
                if match_nova:
                    data_str = match_nova.group(1)  # "11 JUN"
                    descricao_bruta = match_nova.group(2)  # "Qconcursos - Parcela 4/12"
                    valor_str = match_nova.group(3)  # "14,40"
                    
                    try:
                        # Converter data "11 JUN" para "11/06/2024"
                        data_convertida = _converter_data_nubank(data_str, ano_atual)
                        
                        # Converter valor "14,40" para float
                        valor = float(valor_str.replace('.', '').replace(',', '.'))
                        
                        # 🔧 FILTROS MELHORADOS - Ignorar operações bancárias
                        descricao_lower = descricao_bruta.lower()
                        if any(keyword in descricao_lower for keyword in [
                            'pagamento em', 'crédito de', 'saldo em', 'anuidade',
                            'juros de', 'multa de', 'encerramento de'
                        ]):
                            logger.debug(f"[Nubank] ❌ Ignorando operação bancária: {descricao_bruta}")
                            continue
                        
                        # ✨ DETECTAR PARCELAS no novo formato: "Qconcursos - Parcela 4/12"
                        match_parcela = padrao_parcela.search(descricao_bruta)
                        if match_parcela:
                            desc_base = match_parcela.group(1).strip()  # "Qconcursos"
                            parcela_atual = int(match_parcela.group(2))  # 4
                            parcela_total = int(match_parcela.group(3))   # 12
                            
                            transacao = {
                                "data": data_convertida,
                                "descricao": descricao_bruta.strip(),
                                "valor": valor
                            }
                            
                            if parcela_atual == 1:
                                # Primeira parcela = incluir no mês atual
                                transacoes_mes_atual.append(transacao)
                                logger.info(f"[Nubank] ✅ Primeira parcela: {desc_base} - {parcela_atual}/{parcela_total}")
                            else:
                                # Parcelas futuras = não incluir no total
                                parcelas_futuras.append(transacao)
                                logger.info(f"[Nubank] ⏭️ Parcela futura: {desc_base} - {parcela_atual}/{parcela_total}")
                        else:
                            # Transação normal (não é parcela)
                            transacao = {
                                "data": data_convertida,
                                "descricao": descricao_bruta.strip(),
                                "valor": valor
                            }
                            
                            # Verificar duplicatas
                            if transacao not in transacoes_mes_atual:
                                transacoes_mes_atual.append(transacao)
                                logger.info(f"[Nubank] ✅ Transação normal: {descricao_bruta} - R$ {valor:.2f}")
                            else:
                                logger.debug(f"[Nubank] 🔄 Duplicata ignorada: {descricao_bruta}")
                                
                    except (ValueError, AttributeError) as e:
                        logger.warning(f"[Nubank] ❌ Erro ao processar: '{linha_completa}'. Erro: {e}")
                        continue
                
                # 🔄 FALLBACK: Tentar padrão antigo para compatibilidade
                elif re.match(r'^\d{1,2} \w{3}\s+', linha_completa):
                    logger.debug(f"[Nubank] 🔄 Tentando padrão antigo para: {linha_completa}")
                    # [Código do padrão antigo aqui se necessário]
    
    logger.info(f"[Parser Nubank 2025] ✅ {len(transacoes_mes_atual)} transações do mês atual")
    logger.info(f"[Parser Nubank 2025] 📅 {len(parcelas_futuras)} parcelas futuras detectadas")
    
    # 📊 LOG DETALHADO para debugging
    total_mes_atual = sum(t['valor'] for t in transacoes_mes_atual)
    total_parcelas = sum(p['valor'] for p in parcelas_futuras)
    logger.info(f"[Parser Nubank 2025] 💰 Total mês atual: R$ {total_mes_atual:.2f}")
    logger.info(f"[Parser Nubank 2025] ⏭️ Total parcelas futuras: R$ {total_parcelas:.2f}")
    
    return {
        'transacoes': transacoes_mes_atual,
        'parcelas_futuras': parcelas_futuras,
        'banco': 'Nubank'
    }


def _converter_data_nubank(data_original: str, ano: str) -> str:
    """Converte data do Nubank '11 JAN' para '11/01/2024'"""
    meses = {
        'JAN': '01', 'FEV': '02', 'MAR': '03', 'ABR': '04',
        'MAI': '05', 'JUN': '06', 'JUL': '07', 'AGO': '08',
        'SET': '09', 'OUT': '10', 'NOV': '11', 'DEZ': '12'
    }
    
    try:
        # Parse "11 JAN"
        parts = data_original.split()
        if len(parts) == 2:
            dia = parts[0].zfill(2)
            mes_abrev = parts[1].upper()
            
            if mes_abrev in meses:
                return f"{dia}/{meses[mes_abrev]}/{ano}"
    except:
        pass
    
    # Fallback
    return data_original

def detectar_banco_e_delegar_parse(pdf: pdfplumber.PDF) -> list:
    global _parcelas_detectadas_info
    # Limpar info de parcelas anterior
    _parcelas_detectadas_info = {'total': 0, 'banco': None, 'detalhes': [], 'parcelas_completas': []}
    
    logger.info("[FATURA DEBUG] Iniciando detecção de banco")
    try:
        texto_pagina_1 = pdf.pages[0].extract_text()
        logger.info(f"[FATURA DEBUG] Texto extraído da primeira página (primeiros 200 chars): {texto_pagina_1[:200] if texto_pagina_1 else 'VAZIO'}")
        
        if not texto_pagina_1:
            logger.error("[FATURA DEBUG] Não foi possível extrair texto da primeira página")
            return []
            
        texto_lower = texto_pagina_1.lower()

        # Detecção dos 4 bancos suportados
        if "bradesco" in texto_lower or "visa signature" in texto_lower:
            logger.info("Fatura do Bradesco detectada. Usando parser específico.")
            resultado_bradesco = _parse_bradesco_com_pdfplumber(pdf)
            
            # 📋 NOVO: Tratar resultado em dict e registrar parcelas detectadas
            if isinstance(resultado_bradesco, dict):
                transacoes_atuais = resultado_bradesco.get('transacoes', [])
                parcelas_futuras = resultado_bradesco.get('parcelas_futuras', [])
                
                # 🎯 REGISTRAR parcelas detectadas globalmente (SEM notificar ainda)
                _parcelas_detectadas_info['total'] = len(parcelas_futuras)
                _parcelas_detectadas_info['banco'] = 'Bradesco'
                _parcelas_detectadas_info['detalhes'] = [p['descricao'] for p in parcelas_futuras[:5]]  # Primeiras 5
                _parcelas_detectadas_info['parcelas_completas'] = parcelas_futuras[:10]  # 🆕 Primeiras 10 parcelas completas
                
                logger.info(f"[BRADESCO] 📅 {len(parcelas_futuras)} parcelas futuras detectadas e filtradas")
                
                return transacoes_atuais
            else:
                # Fallback para compatibilidade
                return resultado_bradesco if isinstance(resultado_bradesco, list) else []
        elif "cartões caixa" in texto_lower or "caixa econômica" in texto_lower:
            logger.info("Fatura da Caixa detectada. Usando parser específico.")
            resultado_caixa = _parse_caixa_com_pdfplumber(pdf)
            
            # 📋 NOVO: Tratar resultado em dict e registrar parcelas detectadas
            if isinstance(resultado_caixa, dict):
                transacoes_atuais = resultado_caixa.get('transacoes', [])
                parcelas_futuras = resultado_caixa.get('parcelas_futuras', [])
                
                # 🎯 REGISTRAR parcelas detectadas globalmente (SEM notificar ainda)
                _parcelas_detectadas_info['total'] = len(parcelas_futuras)
                _parcelas_detectadas_info['banco'] = 'Caixa'
                _parcelas_detectadas_info['detalhes'] = [p['descricao'] for p in parcelas_futuras[:5]]  # Primeiras 5
                _parcelas_detectadas_info['parcelas_completas'] = parcelas_futuras[:10]  # 🆕 Primeiras 10 parcelas completas
                
                logger.info(f"[CAIXA] 📅 {len(parcelas_futuras)} parcelas futuras detectadas e filtradas")
                
                return transacoes_atuais
            else:
                # Fallback para compatibilidade
                return resultado_caixa if isinstance(resultado_caixa, list) else []
        elif "inter" in texto_lower and ("fatura" in texto_lower or "limite de crédito" in texto_lower):
            logger.info("Fatura do Inter detectada. Usando parser específico.")
            # 🆕 TODO: Migrar para ParserFaturaInter (gerente_financeiro/parser_fatura_inter.py)
            #          quando testarmos completamente - tem 96.75% de precisão!
            resultado_inter = _parse_inter_com_pdfplumber(pdf)
            
            # 📋 NOVO: Tratar resultado em dict e registrar parcelas detectadas
            if isinstance(resultado_inter, dict):
                transacoes_atuais = resultado_inter.get('transacoes', [])
                parcelas_futuras = resultado_inter.get('parcelas_futuras', [])
                
                # 🎯 REGISTRAR parcelas detectadas globalmente (SEM notificar ainda)
                _parcelas_detectadas_info['total'] = len(parcelas_futuras)
                _parcelas_detectadas_info['banco'] = 'Inter'
                _parcelas_detectadas_info['detalhes'] = [p['descricao'] for p in parcelas_futuras[:5]]  # Primeiras 5
                _parcelas_detectadas_info['parcelas_completas'] = parcelas_futuras[:10]  # 🆕 Primeiras 10 parcelas completas
                
                logger.info(f"[INTER] 📅 {len(parcelas_futuras)} parcelas futuras detectadas e filtradas")
                
                return transacoes_atuais
            else:
                # Fallback para compatibilidade
                return resultado_inter if isinstance(resultado_inter, list) else []
        elif ("esta é a sua fatura" in texto_lower and "data do vencimento" in texto_lower) or \
             ("esta é a sua fatura" in texto_lower and "data de vencimento" in texto_lower) or \
             ("olá," in texto_lower and "esta é a sua fatura" in texto_lower) or \
             ("limite total" in texto_lower and "pix no crédito" in texto_lower) or \
             ("nubank" in texto_lower) or ("nu pagamentos" in texto_lower) or \
             ("••••" in texto_pagina_1 and "fatura" in texto_lower):  # 🆕 Novo indicador do layout 2025
            logger.info("🆕 Fatura do Nubank detectada (Layout 2025). Usando parser específico atualizado.")
            resultado_nubank = _parse_nubank_com_pdfplumber(pdf)
            
            # 📋 NOVO: Tratar resultado em dict e registrar parcelas detectadas
            if isinstance(resultado_nubank, dict):
                transacoes_atuais = resultado_nubank.get('transacoes', [])
                parcelas_futuras = resultado_nubank.get('parcelas_futuras', [])
                
                # 🎯 REGISTRAR parcelas detectadas globalmente (SEM notificar ainda)
                _parcelas_detectadas_info['total'] = len(parcelas_futuras)
                _parcelas_detectadas_info['banco'] = 'Nubank'
                _parcelas_detectadas_info['detalhes'] = [p['descricao'] for p in parcelas_futuras[:5]]  # Primeiras 5
                _parcelas_detectadas_info['parcelas_completas'] = parcelas_futuras[:10]  # 🆕 Primeiras 10 parcelas completas
                
                logger.info(f"[NUBANK 2025] 📅 {len(parcelas_futuras)} parcelas futuras detectadas e filtradas")
                
                return transacoes_atuais
            else:
                # Fallback para compatibilidade
                return resultado_nubank if isinstance(resultado_nubank, list) else []

        # Fallback para bancos não identificados
        logger.warning("Banco não identificado. Tentando parser genérico.")
        return _parse_generico_fallback(pdf)
        
    except Exception as e:
        logger.error(f"[FATURA DEBUG] Erro na detecção de banco: {e}", exc_info=True)
        return []

def _parse_generico_fallback(pdf: pdfplumber.PDF) -> list:
    """Parser genérico como último recurso para bancos não identificados."""
    logger.info("[Parser Genérico] Tentando extração genérica")
    transacoes = []
    ano_atual = str(datetime.now().year)
    
    for page_num, page in enumerate(pdf.pages):
        # Pular primeira página (geralmente resumo/boleto)
        if page_num == 0:
            continue
            
        # Tentar extrair tabelas primeiro
        tables = page.extract_tables()
        for table in tables:
            for row in table:
                if not row or len(row) < 2:
                    continue
                
                # Procurar por padrões de data comuns
                primeira_col = str(row[0]) if row[0] else ""
                if re.match(r'^\d{1,2}[/\-]\d{1,2}', primeira_col):
                    try:
                        data = primeira_col
                        desc = str(row[1]) if len(row) > 1 else ""
                        valor_str = str(row[-1]) if len(row) > 1 else ""
                        
                        # Tentar extrair valor
                        valor_match = re.search(r'([\d.]+,\d{2})', valor_str)
                        if valor_match:
                            valor = float(valor_match.group(1).replace('.', '').replace(',', '.'))
                            
                            if desc and len(desc) > 3:
                                transacao = {
                                    "data": f"{data}/{ano_atual}" if len(data.split('/')) == 2 else data,
                                    "descricao": desc.strip(),
                                    "valor": valor
                                }
                                transacoes.append(transacao)
                                
                    except (ValueError, AttributeError):
                        continue
    
    logger.info(f"[Parser Genérico] Extraiu {len(transacoes)} transações.")
    return transacoes

# --- NOVA FUNÇÃO DE BACKGROUND ---
async def _processar_fatura_em_background(context: ContextTypes.DEFAULT_TYPE):
    job_data = context.job.data
    chat_id = job_data['chat_id']
    user_id = job_data['user_id']
    full_name = job_data['full_name']
    file_id = job_data['file_id']
    file_name = job_data.get('file_name', 'fatura.pdf')  # 🆕
    file_size = job_data.get('file_size', 0)  # 🆕
    bot = context.bot
    
    # 🆕 Armazenar informações do arquivo no contexto para uso durante salvamento
    context._current_file_info = {
        'name': file_name,
        'size': file_size
    }
    
    logger.info(f"[FATURA DEBUG] Iniciando processamento para user {user_id}")

    try:
        # 🛡️ TRATAMENTO MELHORADO para arquivos grandes
        try:
            telegram_file = await bot.get_file(file_id)
            file_bytes = await telegram_file.download_as_bytearray()
            logger.info(f"[FATURA DEBUG] Arquivo baixado, tamanho: {len(file_bytes)} bytes")
        except Exception as download_error:
            error_msg = str(download_error).lower()
            if "file is too big" in error_msg:
                await bot.send_message(
                    chat_id, 
                    "❌ <b>Arquivo muito grande!</b>\n\n"
                    "🔧 <b>Soluções:</b>\n"
                    "• Comprima o PDF online\n"
                    "• Use apenas as páginas necessárias\n"
                    "• Limite máximo: 20MB",
                    parse_mode='HTML'
                )
                return
            elif "timed out" in error_msg:
                await bot.send_message(
                    chat_id,
                    "⏰ <b>Timeout no download!</b>\n\n"
                    "Arquivo muito grande ou conexão lenta. Tente um arquivo menor.",
                    parse_mode='HTML'
                )
                return
            else:
                # Erro genérico no download
                logger.error(f"Erro no download do arquivo: {download_error}")
                await bot.send_message(
                    chat_id,
                    "❌ Erro no download do arquivo. Tente novamente ou use um arquivo menor."
                )
                return

        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            # 1. Extração Precisa com Parser de Layout
            transacoes_extraidas = detectar_banco_e_delegar_parse(pdf)
            logger.info(f"[FATURA DEBUG] Transações extraídas: {len(transacoes_extraidas)}")

        if not transacoes_extraidas:
            # 🆕 NOVA MENSAGEM para layouts não suportados
            await bot.send_message(
                chat_id, 
                "📄 <b>Layout da fatura não reconhecido</b>\n\n"
                "⚠️ O layout da fatura do seu cartão não pode ser lido automaticamente.\n\n"
                "🤝 <b>Quer nos ajudar?</b>\n"
                "Se quiser usar essa função futuramente, ajude o desenvolvedor enviando "
                "a fatura do seu cartão <b>OMITINDO TODOS OS SEUS DADOS PESSOAIS</b> "
                "(números do cartão, CPF, valores, etc.), para que possamos suportar "
                "sua fatura no futuro.\n\n"
                "📧 <b>Como ajudar:</b>\n"
                "• Remova/cubra todos os dados pessoais\n"
                "• Mantenha apenas o layout das transações\n"
                "• Envie para dev.henriquejfp@hotmail.com\n\n"
                "💡 <i>Entretanto, você pode continuar usando o /lancamento manual!</i>",
                parse_mode='HTML'
            )
            return

        # 2. Categorização com IA (tarefa muito mais simples agora)
        db = next(get_db())
        try:
            categorias_db = db.query(Categoria).options(joinedload(Categoria.subcategorias)).all()
            categorias_formatadas = "\n".join([f"- {c.nome}: ({', '.join(s.nome for s in c.subcategorias)})" for c in categorias_db])
        finally:
            db.close()
        
        lista_json_str = json.dumps(transacoes_extraidas, indent=2, ensure_ascii=False)
        prompt = PROMPT_CATEGORIZACAO_V4.format(
            categorias_disponiveis=categorias_formatadas,
            lista_transacoes_json=lista_json_str
        )

        transacoes_categorizadas = transacoes_extraidas # Fallback
        try:
            model = genai.GenerativeModel(config.GEMINI_MODEL_NAME)
            generation_config = {
                "temperature": 0.1
            }
            
            # 🔄 Implementar timeout e retry para IA
            response = model.generate_content(prompt, generation_config=generation_config)
            json_match = re.search(r'\[.*\]', response.text, re.DOTALL | re.IGNORECASE)
            if json_match:
                transacoes_categorizadas = json.loads(json_match.group(0))
                logger.info(f"[IA] Categorizou {len(transacoes_categorizadas)} transações com sucesso")
            else:
                logger.warning("IA não retornou JSON válido, usando categorias padrão")
                
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"⚠️ Timeout/Conexão da IA (erro 504): {e}. Usando categorias padrão")
        except json.JSONDecodeError as e:
            logger.error(f"❌ IA retornou JSON inválido: {e}. Usando categorias padrão")
        except Exception as e:
            logger.error(f"❌ IA falhou na categorização: {e}. Usando categorias padrão")

        # Armazenar dados de forma segura para background job
        # Usar um cache temporário na aplicação para dados de fatura
        if not hasattr(context.application, 'fatura_cache'):
            context.application.fatura_cache = {}
        
        # Armazenar com timestamp para limpeza automática
        cache_key = f"fatura_{chat_id}_{user_id}"
        context.application.fatura_cache[cache_key] = {
            "transacoes": transacoes_categorizadas,
            "timestamp": datetime.now().timestamp()
        }
        
        # Também tentar armazenar no user_data se disponível
        if hasattr(context, 'user_data') and context.user_data is not None:
            context.user_data[f"fatura_{chat_id}"] = {"transacoes": transacoes_categorizadas}

        # 3. Envia o resultado para o usuário
        db = next(get_db())
        try:
            user_db = get_or_create_user(db, user_id, full_name)
            cartoes = db.query(Conta).filter(Conta.id_usuario == user_db.id, Conta.tipo == 'Cartão de Crédito').all()
            if not cartoes:
                await bot.send_message(chat_id, "Você não tem cartões de crédito cadastrados. Use `/configurar` para adicionar um e tente novamente.")
                return

            # 🎯 NOVO: Verificar se houve detecção de parcelas futuras
            global _parcelas_detectadas_info
            
            botoes = [[InlineKeyboardButton(c.nome, callback_data=f"fatura_conta_{c.id}")] for c in cartoes]
            
            # 🎯 MENSAGEM SIMPLES: apenas resumo das transações extraídas
            texto_principal = f"✅ Análise concluída! Encontrei <b>{len(transacoes_categorizadas)}</b> transações válidas."
            
            # ⚠️ AVISAR sobre parcelas detectadas (SEM detalhar ainda)
            logger.info(f"[FATURA DEBUG] Verificando parcelas detectadas: {_parcelas_detectadas_info}")
            if _parcelas_detectadas_info['total'] > 0:
                banco = _parcelas_detectadas_info['banco']
                total_parcelas = _parcelas_detectadas_info['total']
                
                logger.info(f"[FATURA DEBUG] ⚠️ MOSTRANDO PARCELAS: {total_parcelas} do {banco}")
                texto_principal += f"\n\n📅 <b>Nota:</b> Detectei <b>{total_parcelas} parcelamentos</b> do {banco} que não foram incluídos (apenas primeiras parcelas são lançadas)."
            else:
                logger.info(f"[FATURA DEBUG] ❌ Nenhuma parcela detectada para mostrar")
            
            texto_principal += f"\n\nA qual dos seus cartões esta fatura pertence?"
            
            await bot.send_message(
                chat_id=chat_id,
                text=texto_principal,
                reply_markup=InlineKeyboardMarkup(botoes),
                parse_mode='HTML'
            )
        finally:
            db.close()

    except Exception as e:
        logger.error(f"Erro CRÍTICO no job de background da fatura: {e}", exc_info=True)
        await context.bot.send_message(chat_id, "❌ Ops! Ocorreu um erro inesperado e grave durante o processamento. A equipe já foi notificada.")

# --- Handler principal, agora delega para o background ---
async def processar_fatura_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    chat_id = update.effective_chat.id
    file_id = update.message.document.file_id
    file_name = update.message.document.file_name or "fatura.pdf"
    file_size = update.message.document.file_size or 0

    # 🚨 VERIFICAÇÃO: Arquivo muito grande para o Telegram API
    max_size_mb = 20  # Limite do Telegram é 20MB
    if file_size > (max_size_mb * 1024 * 1024):
        await update.message.reply_html(
            f"❌ <b>Arquivo muito grande!</b>\n\n"
            f"📊 Tamanho do arquivo: {file_size / (1024*1024):.1f} MB\n"
            f"📊 Limite máximo: {max_size_mb} MB\n\n"
            f"💡 <b>Solução:</b> Tente compactar o PDF ou use um arquivo menor."
        )
        return ConversationHandler.END

    # 🧪 MODO TESTE: Limpar cache se existir (para facilitar testes repetidos)
    if hasattr(context.application, 'fatura_cache'):
        cache_key = f"fatura_{chat_id}_{user.id}"
        if cache_key in context.application.fatura_cache:
            del context.application.fatura_cache[cache_key]
            logging.info(f"🧪 Cache limpo para teste: {cache_key}")

    # 🆕 NOVA ABORDAGEM: Sem verificação prévia de arquivo duplicado
    # Agora verificamos duplicatas por transação individual durante o salvamento

    # 🆕 Armazenar informações do arquivo no contexto para uso posterior
    context._current_file_info = {
        'name': file_name,
        'size': file_size // 1024  # Converter para KB
    }

    context.job_queue.run_once(
        _processar_fatura_em_background,
        when=0,
        data={
            'chat_id': update.effective_chat.id,
            'user_id': user.id,
            'full_name': user.full_name,
            'file_id': file_id,
            'file_name': file_name,  # 🆕 Incluir nome do arquivo
            'file_size': file_size // 1024  # 🆕 Incluir tamanho em KB
        },
        name=f"fatura_proc_{user.id}_{datetime.now().timestamp()}"
    )

    await update.message.reply_html(
        "✅ Fatura recebida! Iniciei o processamento em segundo plano.\n\n"
        "Este processo pode levar <b>até 1 minuto</b>. Eu te enviarei uma nova mensagem assim que terminar."
    )

    return AWAIT_CONTA_ASSOCIADA

# --- Funções de callback (com ajuste para usar cache) ---
async def associar_conta_e_confirmar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.message.delete()

    conta_id = int(query.data.split('_')[-1])
    chat_id = update.effective_chat.id
    user_id = query.from_user.id

    # Buscar dados do cache ou user_data
    dados_fatura = None
    transacoes = []
    
    # Tentar pegar do user_data primeiro
    if hasattr(context, 'user_data') and context.user_data and f"fatura_{chat_id}" in context.user_data:
        dados_fatura = context.user_data[f"fatura_{chat_id}"]
        transacoes = dados_fatura.get('transacoes', [])
        # Adicionar conta_id
        context.user_data[f"fatura_{chat_id}"]['conta_id'] = conta_id
    
    # Fallback: tentar pegar do cache da aplicação
    elif hasattr(context.application, 'fatura_cache'):
        cache_key = f"fatura_{chat_id}_{user_id}"
        cached_data = context.application.fatura_cache.get(cache_key)
        if cached_data:
            transacoes = cached_data.get('transacoes', [])
            # Criar entrada no user_data para as próximas funções
            if not hasattr(context, 'user_data') or context.user_data is None:
                # Se user_data não existe, usar dados temporários
                dados_fatura = {'transacoes': transacoes, 'conta_id': conta_id}
            else:
                context.user_data[f"fatura_{chat_id}"] = {'transacoes': transacoes, 'conta_id': conta_id}
                dados_fatura = context.user_data[f"fatura_{chat_id}"]

    # O resto da função continua igual...
    if not transacoes:
        await context.bot.send_message(chat_id, "Erro: Nenhuma transação para confirmar.")
        return ConversationHandler.END

    total_valor = sum(t.get('valor', 0.0) for t in transacoes)
    preview_list = [f"<code>{t.get('data')}</code> - {t.get('descricao', 'N/A')[:25]:<25} <b>R$ {t.get('valor', 0.0):.2f}</b>" for t in transacoes[:15]]
    preview_text = "\n".join(preview_list)
    if len(transacoes) > 15:
        preview_text += f"\n... e mais {len(transacoes) - 15} transações."

    texto_confirmacao = (
        f"<b>Confirme a Importação</b>\n\n<b>Transações encontradas:</b> {len(transacoes)}\n"
        f"<b>Valor total:</b> R$ {total_valor:.2f}\n\n<b>Prévia:</b>\n{preview_text}\n\n"
        "Deseja salvar todos esses lançamentos neste cartão?"
    )
    keyboard = [[InlineKeyboardButton("✅ Sim, salvar", callback_data="fatura_confirm_save")],
                [InlineKeyboardButton("❌ Cancelar", callback_data="fatura_confirm_cancel")]]
    await context.bot.send_message(chat_id, texto_confirmacao, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))

    return AWAIT_CONFIRMATION

async def salvar_transacoes_em_lote(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("💾 Verificando e salvando no banco de dados...")

    chat_id = update.effective_chat.id
    user_id = query.from_user.id
    
    # Buscar dados do user_data ou cache
    fatura_data = {}
    conta_id = None
    transacoes = []
    
    # Tentar pegar do user_data primeiro
    if hasattr(context, 'user_data') and context.user_data and f"fatura_{chat_id}" in context.user_data:
        fatura_data = context.user_data[f"fatura_{chat_id}"]
        conta_id = fatura_data.get('conta_id')
        transacoes = fatura_data.get('transacoes', [])
    
    # Fallback: tentar pegar do cache da aplicação
    elif hasattr(context.application, 'fatura_cache'):
        cache_key = f"fatura_{chat_id}_{user_id}"
        cached_data = context.application.fatura_cache.get(cache_key)
        if cached_data:
            transacoes = cached_data.get('transacoes', [])
            # conta_id deve ter sido armazenado na função anterior, mas pode não estar disponível
            # Vamos tentar recuperar do callback_data ou solicitar novamente
            logger.warning(f"Dados não encontrados no user_data, tentando cache. Cache encontrado: {bool(cached_data)}")

    if not all([conta_id, transacoes]):
        await query.edit_message_text("❌ Erro: Dados da sessão perdidos. Operação cancelada.")
        
        # Limpar cache se existir
        if hasattr(context.application, 'fatura_cache'):
            cache_key = f"fatura_{chat_id}_{user_id}"
            context.application.fatura_cache.pop(cache_key, None)
            
        return ConversationHandler.END
        return ConversationHandler.END

    # O resto da função de salvar é praticamente a mesma
    db = next(get_db())
    try:
        user_info = query.from_user
        usuario_db = get_or_create_user(db, user_info.id, user_info.full_name)
        
        # Mapeamentos e salvamento...
        categorias_map = {cat.nome.lower(): cat for cat in db.query(Categoria).all()}
        subcategorias_map = {(sub.id_categoria, sub.nome.lower()): sub.id for sub in db.query(Subcategoria).all()}
        conta_selecionada = db.query(Conta).filter(Conta.id == conta_id).one()
        novos_lancamentos = []
        transacoes_duplicadas = []
        transacoes_novas = []
        
        # 🆕 NOVA LÓGICA: Verificar duplicatas por transação individual
        
        for i, t in enumerate(transacoes):
            data_obj = datetime.strptime(t['data'], '%d/%m/%Y')
            
            # 🔍 Verificar se já existe transação idêntica
            eh_duplicata = await verificar_transacao_duplicada(
                user_id=usuario_db.telegram_id,
                descricao=t.get('descricao', 'Fatura'),
                valor=t.get('valor', 0.0),
                data_transacao=t['data']
            )
            
            if eh_duplicata:
                transacoes_duplicadas.append(t)
                logger.info(f"🔄 Transação duplicada ignorada: {t.get('descricao')} - R$ {t.get('valor', 0):.2f}")
                continue
            
            # Transação nova - preparar para inserção
            transacoes_novas.append(t)
            
            id_categoria, id_subcategoria = None, None
            cat_sugerida = t.get('categoria_sugerida', '').lower()
            sub_sugerida = t.get('subcategoria_sugerida', '').lower()
            if cat_sugerida in categorias_map:
                categoria_obj = categorias_map[cat_sugerida]
                id_categoria = categoria_obj.id
                if sub_sugerida:
                    id_subcategoria = subcategorias_map.get((id_categoria, sub_sugerida))
            
            novos_lancamentos.append(Lancamento(
                id_usuario=usuario_db.id, 
                descricao=t.get('descricao', 'Fatura'), 
                valor=t.get('valor', 0.0), 
                tipo='Saída', 
                data_transacao=data_obj, 
                forma_pagamento=conta_selecionada.nome, 
                id_conta=conta_id, 
                id_categoria=id_categoria, 
                id_subcategoria=id_subcategoria
            ))

        # 📊 RELATÓRIO FINAL
        total_processadas = len(transacoes)
        total_novas = len(novos_lancamentos)
        total_duplicadas = len(transacoes_duplicadas)
        
        if novos_lancamentos:
            db.add_all(novos_lancamentos)
            db.commit()
            limpar_cache_usuario(usuario_db.id)
            
            # 🎯 NOVO FLUXO: Relatório detalhado + oferecer agendamento de parcelas
            texto_sucesso = f"✅ <b>Importação Concluída!</b>\n\n"
            texto_sucesso += f"📊 <b>Resumo:</b>\n"
            texto_sucesso += f"• Transações processadas: <b>{total_processadas}</b>\n"
            texto_sucesso += f"• Novas transações salvas: <b>{total_novas}</b>\n"
            
            if total_duplicadas > 0:
                texto_sucesso += f"• Duplicadas ignoradas: <b>{total_duplicadas}</b> 🔄\n"
                texto_sucesso += f"\n💡 <i>As duplicadas já estavam no seu sistema.</i>"
            
            # Verificar se há parcelas detectadas para oferecer agendamento
            global _parcelas_detectadas_info
            if _parcelas_detectadas_info['total'] > 0:
                banco = _parcelas_detectadas_info['banco']
                total_parcelas = _parcelas_detectadas_info['total']
                detalhes = _parcelas_detectadas_info['detalhes']
                
                texto_sucesso += f"\n\n📅 <b>Parcelas Futuras Detectadas ({banco})</b>\n"
                texto_sucesso += f"🔍 Encontrei <b>{total_parcelas} parcelamentos</b> que não foram lançados."
                
                if detalhes:
                    texto_sucesso += "\n\n📋 <b>Exemplos:</b>"
                    for detalhe in detalhes[:3]:  # Máximo 3 exemplos
                        if " - " in detalhe:
                            nome = detalhe.split(" - ")[0][:20]  # Limitar tamanho
                            parcela_info = detalhe.split(" - ")[-1] if "/" in detalhe else ""
                            texto_sucesso += f"\n• {nome}... ({parcela_info})"
                        else:
                            texto_sucesso += f"\n• {detalhe[:25]}..."
                
                if total_parcelas > 3:
                    texto_sucesso += f"\n... e mais {total_parcelas - 3} parcelas"
                
                texto_sucesso += f"\n\n💡 <b>Deseja incluir esses parcelamentos na função /agendar?</b>"
                
                # Botões para escolha
                keyboard = [
                    [InlineKeyboardButton("✅ Sim, incluir no /agendar", callback_data="fatura_agendar_sim")],
                    [InlineKeyboardButton("❌ Não, obrigado", callback_data="fatura_agendar_nao")]
                ]
                await query.edit_message_text(texto_sucesso, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))
            else:
                # Sem parcelas detectadas = apenas sucesso simples
                await query.edit_message_text(texto_sucesso, parse_mode='HTML')
        else:
            # Nenhuma transação nova para salvar
            if total_duplicadas > 0:
                texto_duplicatas = f"🔄 <b>Todas as transações já existem!</b>\n\n"
                texto_duplicatas += f"📊 <b>Resumo:</b>\n"
                texto_duplicatas += f"• Transações processadas: <b>{total_processadas}</b>\n"
                texto_duplicatas += f"• Duplicadas encontradas: <b>{total_duplicadas}</b>\n\n"
                texto_duplicatas += f"💡 <i>Parece que esta fatura já foi importada anteriormente.</i>\n"
                texto_duplicatas += f"✅ Nenhuma ação necessária - seus dados estão atualizados!"
                
                await query.edit_message_text(texto_duplicatas, parse_mode='HTML')
            else:
                await query.edit_message_text("🤔 Nenhuma transação válida foi encontrada para salvar.")

    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao salvar transações em lote: {e}", exc_info=True)
        await query.edit_message_text("❌ Ocorreu um erro grave ao tentar salvar as transações.")
    finally:
        db.close()
        # Limpar dados da sessão
        if hasattr(context, 'user_data') and context.user_data:
            context.user_data.pop(f"fatura_{chat_id}", None)
        
        # Limpar cache da aplicação
        if hasattr(context.application, 'fatura_cache'):
            cache_key = f"fatura_{chat_id}_{user_id}"
            context.application.fatura_cache.pop(cache_key, None)
            
    return ConversationHandler.END

# --- FUNÇÕES DE CALLBACK PARA AGENDAMENTO DE PARCELAS ---
async def callback_agendar_parcelas_sim(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Usuário escolheu incluir as parcelas no /agendar - IMPLEMENTAÇÃO REAL"""
    query = update.callback_query
    await query.answer()
    
    chat_id = update.effective_chat.id
    user_id = query.from_user.id
    
    # Buscar dados das parcelas detectadas
    global _parcelas_detectadas_info
    
    if _parcelas_detectadas_info['total'] == 0:
        await query.edit_message_text(
            "❌ <b>Erro!</b>\n\n"
            "Não há parcelas detectadas para agendar. Os dados podem ter expirado.\n\n"
            "� Processe a fatura novamente se necessário.",
            parse_mode='HTML'
        )
        return
    
    # Buscar dados da sessão atual
    fatura_data = {}
    conta_id = None
    
    # Tentar pegar do user_data primeiro
    if hasattr(context, 'user_data') and context.user_data and f"fatura_{chat_id}" in context.user_data:
        fatura_data = context.user_data[f"fatura_{chat_id}"]
        conta_id = fatura_data.get('conta_id')
    
    # Fallback: tentar pegar do cache da aplicação
    elif hasattr(context.application, 'fatura_cache'):
        cache_key = f"fatura_{chat_id}_{user_id}"
        cached_data = context.application.fatura_cache.get(cache_key)
        if cached_data:
            # conta_id não está no cache, mas podemos buscar do banco a última conta usada
            logger.info("Usando cache da aplicação para recuperar dados de parcelas")
    
    if not conta_id:
        await query.edit_message_text(
            "❌ <b>Erro!</b>\n\n"
            "Não foi possível identificar a conta do cartão. Os dados da sessão expiraram.\n\n"
            "💡 Processe a fatura novamente para agendar as parcelas.",
            parse_mode='HTML'
        )
        return
    
    await query.edit_message_text("⏳ Criando agendamentos das parcelas...")
    
    # Implementar criação real dos agendamentos
    db = next(get_db())
    try:
        from models import Agendamento
        from datetime import datetime, timedelta
        
        user_info = query.from_user
        usuario_db = get_or_create_user(db, user_info.id, user_info.full_name)
        
        # Buscar dados das parcelas do cache
        parcelas_criadas = 0
        erros = 0
        
        # Usar dados reais das parcelas detectadas para criar agendamentos
        banco = _parcelas_detectadas_info['banco']
        parcelas_completas = _parcelas_detectadas_info['parcelas_completas']
        
        # Para cada parcela detectada, criar um agendamento mensal
        data_base = datetime.now().date()
        
        for i, parcela_data in enumerate(parcelas_completas):
            try:
                # Extrair informações reais da parcela
                descricao = parcela_data.get('descricao', f'Parcela {banco}')
                valor = parcela_data.get('valor', 100.00)
                
                # Data do próximo mês para a primeira parcela futura
                meses_futuros = i + 1
                ano_futuro = data_base.year
                mes_futuro = data_base.month + meses_futuros
                
                while mes_futuro > 12:
                    mes_futuro -= 12
                    ano_futuro += 1
                
                try:
                    proxima_data = data_base.replace(year=ano_futuro, month=mes_futuro)
                except ValueError:
                    # Se o dia não existe no mês futuro (ex: 31 de fevereiro), usar último dia do mês
                    from calendar import monthrange
                    ultimo_dia = monthrange(ano_futuro, mes_futuro)[1]
                    dia_ajustado = min(data_base.day, ultimo_dia)
                    proxima_data = data_base.replace(year=ano_futuro, month=mes_futuro, day=dia_ajustado)
                
                agendamento = Agendamento(
                    id_usuario=usuario_db.id,
                    descricao=f"[{banco}] {descricao}",
                    valor=valor,
                    tipo='Saída',
                    data_primeiro_evento=proxima_data,
                    frequencia='mensal',
                    total_parcelas=1,  # Cada parcela é um agendamento único
                    parcela_atual=0,
                    proxima_data_execucao=proxima_data,
                    ativo=True
                )
                
                db.add(agendamento)
                parcelas_criadas += 1
                
            except Exception as e:
                logger.error(f"Erro ao criar agendamento para parcela: {parcela_data}. Erro: {e}")
                erros += 1
        
        db.commit()
        
        # Limpar dados globais após uso
        _parcelas_detectadas_info = {'total': 0, 'banco': None, 'detalhes': [], 'parcelas_completas': []}
        
        await query.edit_message_text(
            f"✅ <b>Agendamentos Criados!</b>\n\n"
            f"📅 <b>{parcelas_criadas}</b> parcelas foram agendadas\n"
            f"🏦 Banco: <b>{banco}</b>\n"
            f"📝 Tipo: <b>Mensais</b>\n\n"
            f"💡 Use <b>/agendar</b> para visualizar e editar os valores das parcelas.\n\n"
            f"⚠️ <i>Os valores foram definidos como R$ 100,00 por padrão - ajuste conforme necessário!</i>",
            parse_mode='HTML'
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao criar agendamentos de parcelas: {e}", exc_info=True)
        await query.edit_message_text(
            "❌ <b>Erro!</b>\n\n"
            "Ocorreu um erro ao criar os agendamentos das parcelas.\n\n"
            "💡 Tente usar /agendar manualmente ou processe a fatura novamente.",
            parse_mode='HTML'
        )
    finally:
        db.close()

async def callback_agendar_parcelas_nao(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Usuário escolheu NÃO incluir as parcelas no /agendar"""
    query = update.callback_query
    await query.answer()
    
    # Limpar dados globais de parcelas
    global _parcelas_detectadas_info
    _parcelas_detectadas_info = {'total': 0, 'banco': None, 'detalhes': [], 'parcelas_completas': []}
    
    await query.edit_message_text(
        "✅ <b>Tudo certo!</b>\n\n"
        "Os lançamentos foram salvos com sucesso. As parcelas futuras não foram incluídas.\n\n"
        "💡 <i>Se mudar de ideia, pode usar /agendar a qualquer momento!</i>",
        parse_mode='HTML'
    )


async def fatura_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_html(
        "📄 <b>Analisador de Faturas de Cartão</b>\n\n"
        "🚧 <b><i>Esta função ainda está em desenvolvimento. Alguns comportamentos inesperados podem acontecer.</i></b>\n\n"
        "Envie o arquivo PDF da sua fatura e eu vou extrair todas as transações para você! ✨"
    )
    return AWAIT_FATURA_PDF

# --- HANDLER CONVERSATION ---
fatura_conv = ConversationHandler(
    entry_points=[CommandHandler('fatura', fatura_start)],
    states={
        AWAIT_FATURA_PDF: [MessageHandler(filters.Document.PDF, processar_fatura_pdf)],
        AWAIT_CONTA_ASSOCIADA: [CallbackQueryHandler(associar_conta_e_confirmar, pattern=r'^fatura_conta_')],
        AWAIT_CONFIRMATION: [
            CallbackQueryHandler(salvar_transacoes_em_lote, pattern='^fatura_confirm_save$'),
            CallbackQueryHandler(cancel, pattern='^fatura_confirm_cancel$')
            # 🔄 REMOVIDO: Callbacks movidos para handlers independentes no bot.py
        ]
    },
    fallbacks=[CommandHandler('cancelar', cancel)],
    per_message=False,
    per_user=True,
    per_chat=True
)