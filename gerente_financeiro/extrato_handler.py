import csv
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
from datetime import datetime, timedelta, timezone
import io
import fitz  # PyMuPDF

from pdf2image import convert_from_bytes
import google.generativeai as genai
from google.cloud import vision
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler, CallbackQueryHandler, MessageHandler, filters
)
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, func

import config
from database.database import get_db, get_or_create_user, get_db
from models import Conta, Lancamento, ItemLancamento, Categoria, Subcategoria, Usuario
from .handlers import cancel, enviar_texto_em_blocos
from .prompts import PROMPT_ANALISE_EXTRATO
from typing import Dict, List, Tuple

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False
    logger.warning("pdfplumber não está disponível. Usando fallback com PyMuPDF.")

try:
    from PyPDF2 import PdfReader
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False
# --- CONFIGURAÇÃO DE LOG ---

logger = logging.getLogger(__name__)

# --- ESTADOS DA CONVERSA - MOVIDOS PARA states.py ---
from .states import ESCOLHER_CONTA_EXTRATO, CONFIRMAR_EXTRATO, PROCESSAR_EXTRATO

# Mantendo compatibilidade com nomes antigos
AWAIT_EXTRATO_FILE = ESCOLHER_CONTA_EXTRATO
AWAIT_CONTA_ASSOCIADA = CONFIRMAR_EXTRATO  
AWAIT_CONFIRMATION = PROCESSAR_EXTRATO


class ProcessadorDeDocumentos:
    """Classe para agrupar funções relacionadas ao processamento de documentos."""

    def _limpar_linha(self, linha: str) -> str:
        """Remove espaços múltiplos e caracteres indesejados de uma linha."""
        linha_limpa = re.sub(r'\s+', ' ', linha).strip()
        linha_limpa = re.sub(r'[^\w\s.,/()-R$]', '', linha_limpa)
        return linha_limpa

    def processar_pdf(self, file_bytes: bytes) -> str:
        """
        Extrai texto de um PDF de forma inteligente usando múltiplos métodos.
        """
        texto_completo = ""
        
        # MÉTODO 1: Tentar com pdfplumber (melhor para extratos tabulares)
        if PDFPLUMBER_AVAILABLE:
            try:
                import pdfplumber
                with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                    if not pdf.pages:
                        raise ValueError("PDF sem páginas ou corrompido.")

                    for page_num, page in enumerate(pdf.pages):
                        texto_completo += f"\n--- PÁGINA {page_num + 1} ---\n"
                        
                        # Tenta extração com layout preservado
                        texto_pagina = page.extract_text(layout=True, x_tolerance=2, y_tolerance=2)

                        if not texto_pagina:
                            logger.warning(f"Extração com layout falhou na página {page_num + 1}. Tentando método simples.")
                            texto_pagina = page.extract_text()

                        if texto_pagina:
                            linhas_limpas = [self._limpar_linha(linha) for linha in texto_pagina.split('\n') if self._limpar_linha(linha)]
                            texto_completo += "\n".join(linhas_limpas)

                logger.info(f"PDF processado com pdfplumber. Total de caracteres: {len(texto_completo)}")
                if len(texto_completo.strip()) > 100:  # Se conseguiu texto suficiente
                    return texto_completo
            except Exception as e:
                logger.error(f"Erro com pdfplumber: {e}")

        # MÉTODO 2: Tentar com PyMuPDF (fitz)
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            texto_completo = ""
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                texto_completo += f"\n--- PÁGINA {page_num + 1} ---\n"
                
                # Extrai texto da página
                texto_pagina = page.get_text()
                if texto_pagina:
                    linhas_limpas = [self._limpar_linha(linha) for linha in texto_pagina.split('\n') if self._limpar_linha(linha)]
                    texto_completo += "\n".join(linhas_limpas)
            
            doc.close()
            logger.info(f"PDF processado com PyMuPDF. Total de caracteres: {len(texto_completo)}")
            if len(texto_completo.strip()) > 100:
                return texto_completo
        except Exception as e:
            logger.error(f"Erro com PyMuPDF: {e}")

        # MÉTODO 3: Fallback com PyPDF2
        if PYPDF2_AVAILABLE:
            try:
                from PyPDF2 import PdfReader
                pdf_reader = PdfReader(io.BytesIO(file_bytes))
                texto_fallback = ""
                for page_num, page in enumerate(pdf_reader.pages):
                    texto_fallback += f"\n--- PÁGINA {page_num + 1} ---\n"
                    texto_pagina = page.extract_text() or ""
                    if texto_pagina:
                        linhas_limpas = [self._limpar_linha(linha) for linha in texto_pagina.split('\n') if self._limpar_linha(linha)]
                        texto_fallback += "\n".join(linhas_limpas)
                
                logger.info(f"PDF processado com PyPDF2. Total de caracteres: {len(texto_fallback)}")
                if len(texto_fallback.strip()) > 50:
                    return texto_fallback
            except Exception as e:
                logger.error(f"Erro com PyPDF2: {e}")

        # MÉTODO 4: Usar OCR com pdf2image + Google Vision (último recurso)
        try:
            logger.info("Tentando OCR com pdf2image + Google Vision...")
            
            # Converte PDF em imagens
            images = convert_from_bytes(file_bytes, dpi=300, first_page=1, last_page=5)  # Limita a 5 páginas
            
            # Inicializa cliente do Google Vision
            client = vision.ImageAnnotatorClient()
            texto_ocr = ""
            
            for i, image in enumerate(images):
                # Converte imagem para bytes
                img_bytes = io.BytesIO()
                image.save(img_bytes, format='PNG')
                img_bytes = img_bytes.getvalue()
                
                # Faz OCR
                image_vision = vision.Image(content=img_bytes)
                response = client.text_detection(image=image_vision)
                texts = response.text_annotations
                
                if texts:
                    texto_ocr += f"\n--- PÁGINA {i + 1} (OCR) ---\n"
                    page_text = texts[0].description
                    linhas_limpas = [self._limpar_linha(linha) for linha in page_text.split('\n') if self._limpar_linha(linha)]
                    texto_ocr += "\n".join(linhas_limpas)
            
            logger.info(f"OCR concluído. Total de caracteres: {len(texto_ocr)}")
            if len(texto_ocr.strip()) > 50:
                return texto_ocr
                
        except Exception as e:
            logger.error(f"Erro no OCR: {e}")

        raise ValueError("Não foi possível extrair texto do PDF com nenhum dos métodos disponíveis.")
    
    def processar_csv(self, file_bytes: bytes) -> List[Dict]:
        """Processa CSV de forma estruturada, detectando automaticamente o formato."""
        try:
            encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
            texto_csv = None
            
            for encoding in encodings:
                try:
                    texto_csv = file_bytes.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue
            
            if not texto_csv:
                raise ValueError("Não foi possível decodificar o arquivo CSV")
            
            if texto_csv.startswith('\ufeff'):
                texto_csv = texto_csv[1:]
            
            delimitadores = [';', ',', '\t', '|']
            melhor_delimitador = ';'
            max_colunas = 0
            
            for delim in delimitadores:
                linhas = texto_csv.split('\n')[:5]
                total_colunas = sum(len(linha.split(delim)) for linha in linhas if linha.strip())
                if total_colunas > max_colunas:
                    max_colunas = total_colunas
                    melhor_delimitador = delim
            
            reader = csv.DictReader(
                io.StringIO(texto_csv),
                delimiter=melhor_delimitador,
                quotechar='"',
                skipinitialspace=True
            )
            
            transacoes_estruturadas = []
            
            for linha_num, linha in enumerate(reader, 1):
                if not linha or all(not v.strip() for v in linha.values() if v):
                    continue
                
                linha_limpa = {}
                for key, value in linha.items():
                    if key:
                        key_limpa = key.strip().lower()
                        linha_limpa[key_limpa] = value.strip() if value else ""
                
                if self._linha_tem_dados_validos(linha_limpa):
                    transacoes_estruturadas.append({
                        'linha': linha_num,
                        'dados': linha_limpa
                    })
            
            return transacoes_estruturadas
            
        except Exception as e:
            logger.error(f"Erro ao processar CSV: {e}")
            raise
    
    def processar_ofx(self, file_bytes: bytes) -> str:
        """Processa arquivos OFX."""
        try:
            encodings = ['latin-1', 'utf-8', 'cp1252']
            for encoding in encodings:
                try:
                    return file_bytes.decode(encoding, errors='replace')
                except UnicodeDecodeError:
                    continue
            raise ValueError("Não foi possível decodificar o arquivo OFX")
        except Exception as e:
            logger.error(f"Erro ao processar OFX: {e}")
            raise
    
    def _linha_tem_dados_validos(self, linha: Dict) -> bool:
        """Verifica se a linha tem dados válidos para ser considerada uma transação."""
        padrao_data = re.compile(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}')
        padrao_valor = re.compile(r'[\d.,]+')
        
        tem_data = False
        tem_valor = False
        
        for value in linha.values():
            if padrao_data.search(value):
                tem_data = True
            if padrao_valor.search(value) and len(value.replace(',', '').replace('.', '').replace('-', '')) >= 2:
                tem_valor = True
        
        return tem_data and tem_valor
    
    def extrair_valores_numericos(self, texto: str) -> List[float]:
        """Extrai todos os valores numéricos do texto para validação."""
        padroes = [
            r'R\$\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)',
            r'(\d{1,3}(?:\.\d{3})*(?:,\d{2}))',
            r'(\d+,\d{2})',
            r'(\d+\.\d{2})',
        ]
        
        valores = []
        for padrao in padroes:
            matches = re.findall(padrao, texto)
            for match in matches:
                try:
                    valor_str = match.replace('.', '').replace(',', '.')
                    valor = float(valor_str)
                    if valor > 0:
                        valores.append(valor)
                except ValueError:
                    continue
        
        return valores


class ExtratoValidator:
    """Classe para validar dados extraídos do extrato."""
    
    @staticmethod
    def validar_transacao(transacao: Dict) -> Tuple[bool, str]:
        """Valida uma transação individual."""
        campos_obrigatorios = ['data', 'descricao', 'valor']
        
        for campo in campos_obrigatorios:
            if campo not in transacao or not transacao[campo]:
                return False, f"Campo obrigatório '{campo}' ausente"
        
        try:
            data_str = transacao['data']
            if not re.match(r'\d{1,2}/\d{1,2}/\d{4}', data_str):
                return False, f"Data inválida: {data_str}"
            
            datetime.strptime(data_str, '%d/%m/%Y')
        except ValueError:
            return False, f"Data inválida: {transacao['data']}"
        
        try:
            valor = float(transacao['valor'])
            if valor == 0:
                return False, "Valor não pode ser zero"
        except (ValueError, TypeError):
            return False, f"Valor inválido: {transacao['valor']}"
        
        if transacao.get('tipo_transacao') not in ['Entrada', 'Saída']:
            return False, f"Tipo de transação inválido: {transacao.get('tipo_transacao')}"
        
        return True, "Válida"
    
    @staticmethod
    def validar_consistencia_extrato(dados_extrato: Dict, valores_brutos: List[float]) -> Tuple[bool, str]:
        """Valida a consistência geral do extrato."""
        transacoes = dados_extrato.get('transacoes', [])
        
        if not transacoes:
            return False, "Nenhuma transação encontrada"
        
        total_entradas = sum(t['valor'] for t in transacoes if t.get('tipo_transacao') == 'Entrada')
        total_saidas = sum(t['valor'] for t in transacoes if t.get('tipo_transacao') == 'Saída')
        
        todos_valores_transacoes = [t['valor'] for t in transacoes]
        
        valores_encontrados = 0
        for valor in todos_valores_transacoes:
            if any(abs(valor - v) < 0.01 for v in valores_brutos):
                valores_encontrados += 1
        
        taxa_correspondencia = valores_encontrados / len(todos_valores_transacoes)
        
        if taxa_correspondencia < 0.3:
            return False, f"Baixa correspondência de valores ({taxa_correspondencia:.1%})"
        
        return True, f"Consistência OK - {len(transacoes)} transações, correspondência {taxa_correspondencia:.1%}"


# --- FUNÇÕES DO FLUXO ---

async def extrato_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia o fluxo de análise de extrato."""
    await update.message.reply_html(
        "📄 <b>Analisador de Extratos Bancários</b>\n\n"
        "Envie seu extrato em um dos formatos suportados:\n"
        "• <b>PDF</b> - Extratos em formato PDF\n"
        "• <b>CSV</b> - Planilhas com dados estruturados\n"
        "• <b>OFX</b> - Arquivos Open Financial Exchange\n\n"
        "⚡ <b>Processamento Inteligente:</b>\n"
        "• Detecção automática de formato\n"
        "• Validação de dados extraídos\n"
        "• Categorização precisa\n"
        "• Verificação de consistência\n\n"
        "Envie o arquivo e eu cuidarei do resto!"
    )
    return AWAIT_EXTRATO_FILE


async def processar_extrato_arquivo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Recebe o arquivo, extrai o texto bruto e envia para a IA para processamento unificado.
    """
    message = await update.message.reply_text("📥 Extrato recebido! Iniciando processamento...")
    
    try:
        file_source = update.message.document
        mime_type = file_source.mime_type
        file_name = file_source.file_name.lower() if file_source.file_name else ''

        await message.edit_text("📥 Baixando arquivo do Telegram...")
        telegram_file = await file_source.get_file()
        file_bytearray = await telegram_file.download_as_bytearray()
        
        texto_bruto = ""
        
        # Extração de texto bruto unificada
        await message.edit_text("🔎 Extraindo texto do documento...")
        processador = ProcessadorDeDocumentos()
        
        if mime_type == 'application/pdf' or file_name.endswith('.pdf'):
            texto_bruto = processador.processar_pdf(file_bytearray)
        elif mime_type == 'text/csv' or file_name.endswith('.csv'):
            dados_csv = processador.processar_csv(file_bytearray)
            # Converte dados estruturados do CSV em texto para análise da IA
            texto_bruto = ""
            for item in dados_csv:
                linha_dados = []
                for chave, valor in item['dados'].items():
                    linha_dados.append(f"{chave}: {valor}")
                texto_bruto += " | ".join(linha_dados) + "\n"
        elif mime_type in ['application/x-ofx', 'text/plain'] or file_name.endswith('.ofx'):
            texto_bruto = processador.processar_ofx(file_bytearray)
        else:
            await message.edit_text("❌ Formato de arquivo não suportado. Envie um arquivo PDF, CSV ou OFX.")
            return AWAIT_EXTRATO_FILE

        if not texto_bruto or len(texto_bruto.strip()) < 10:
            await message.edit_text("🤔 Não consegui extrair texto válido do arquivo.")
            return ConversationHandler.END

        # Busca categorias para o prompt da IA
        await message.edit_text("📚 Buscando categorias para análise...")
        db: Session = next(get_db())
        try:
            user_db = get_or_create_user(db, update.effective_user.id, update.effective_user.full_name)
            categorias_db = db.query(Categoria).options(joinedload(Categoria.subcategorias)).all()
            categorias_formatadas = [f"- {cat.nome}: ({', '.join(sub.nome for sub in cat.subcategorias)})" for cat in categorias_db]
            categorias_contexto = "\n".join(categorias_formatadas)
        finally:
            db.close()

        # --- PROCESSAMENTO MELHORADO ---
        await message.edit_text("🧠 Analisando o extrato com a IA...")
        
        model = genai.GenerativeModel(config.GEMINI_MODEL_NAME)
        todas_as_transacoes = []
        
        # Primeiro, extrai os totais reais do extrato
        total_entradas_real = 0.0
        total_saidas_real = 0.0
        
        # Busca o resumo no início do extrato
        match_entradas = re.search(r'Total de entradas\s*\+?([\d.,]+)', texto_bruto)
        match_saidas = re.search(r'Total de saídas\s*-?([\d.,]+)', texto_bruto)
        
        if match_entradas:
            total_entradas_real = float(match_entradas.group(1).replace('.', '').replace(',', '.'))
        if match_saidas:
            total_saidas_real = float(match_saidas.group(1).replace('.', '').replace(',', '.'))
        
        logger.info(f"Totais reais do extrato: Entradas=R$ {total_entradas_real:.2f}, Saídas=R$ {total_saidas_real:.2f}")
        
        # TENTATIVA 1: Processar o extrato completo de uma vez
        try:
            prompt_completo = f"""
            IMPORTANTE: Este extrato contém EXATAMENTE:
            - Total de entradas: R$ {total_entradas_real:.2f}
            - Total de saídas: R$ {total_saidas_real:.2f}
            
            Você DEVE extrair TODAS as transações para que os totais batam exatamente.
            
            EXTRATO COMPLETO:
            {texto_bruto[:30000]}
            
            INSTRUÇÕES CRÍTICAS:
            1. Extraia CADA transação individual (transferências, pagamentos, compras, taxas)
            2. NÃO agrupe transações
            3. NÃO pule nenhuma linha que contenha um valor monetário
            4. Cada "Transferência enviada" e "Transferência recebida" é uma transação separada
            5. "Pagamento de fatura" também é uma transação
            6. "Compra no débito" é uma transação
            7. Certifique-se que a soma das entradas seja R$ {total_entradas_real:.2f}
            8. Certifique-se que a soma das saídas seja R$ {total_saidas_real:.2f}
            
            {PROMPT_ANALISE_EXTRATO.format(
                texto_extrato="",
                categorias_disponiveis=categorias_contexto,
                ano_atual=datetime.now().year
            )}
            """
            
            ia_response = await model.generate_content_async(prompt_completo)
            response_text = ia_response.text
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            
            if json_match:
                dados_completos = json.loads(json_match.group(0))
                todas_as_transacoes = dados_completos.get("transacoes", [])
                logger.info(f"Primeira tentativa: {len(todas_as_transacoes)} transações extraídas")
        except Exception as e:
            logger.error(f"Erro na primeira tentativa: {e}")
        
        # TENTATIVA 2: Se não conseguiu todas as transações, processa por seções
        if len(todas_as_transacoes) < 70:  # Esperamos ~76 transações
            await message.edit_text("🔄 Processando extrato em detalhes...")
            todas_as_transacoes = []
            
            # Divide o texto em seções menores
            secoes = []
            linhas = texto_bruto.split('\n')
            secao_atual = []
            
            # Padrão para detectar datas no formato do Nubank
            padrao_data = re.compile(r'^\d{1,2}\s+(JAN|FEV|MAR|ABR|MAI|JUN|JUL|AGO|SET|OUT|NOV|DEZ)\s+\d{4}')
            
            for linha in linhas:
                if padrao_data.match(linha.strip()) and secao_atual:
                    secoes.append('\n'.join(secao_atual))
                    secao_atual = [linha]
                else:
                    secao_atual.append(linha)
            
            if secao_atual:
                secoes.append('\n'.join(secao_atual))
            
            # Processa cada seção
            total_secoes = len(secoes)
            
            for i, secao in enumerate(secoes):
                if not secao.strip():
                    continue
                
                await message.edit_text(f"🧠 Analisando parte {i+1} de {total_secoes}...")
                
                prompt = f"""
                Extraia TODAS as transações desta seção do extrato.
                
                SEÇÃO {i+1} DE {total_secoes}:
                {secao}
                
                REGRAS:
                - Cada linha com "Transferência enviada" é uma transação de SAÍDA
                - Cada linha com "Transferência recebida" é uma transação de ENTRADA  
                - "Pagamento de fatura" é uma transação de SAÍDA
                - "Compra no débito" é uma transação de SAÍDA
                - "Valor adicionado" é uma transação de ENTRADA
                - NÃO pule nenhuma transação
                - Extraia o valor EXATO como aparece no extrato
                
                {PROMPT_ANALISE_EXTRATO.format(
                    texto_extrato="",
                    categorias_disponiveis=categorias_contexto,
                    ano_atual=datetime.now().year
                )}
                """
                
                try:
                    ia_response = await model.generate_content_async(prompt)
                    response_text = ia_response.text
                    json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                    
                    if json_match:
                        dados_secao = json.loads(json_match.group(0))
                        transacoes_secao = dados_secao.get("transacoes", [])
                        todas_as_transacoes.extend(transacoes_secao)
                        logger.info(f"Seção {i+1}: {len(transacoes_secao)} transações extraídas")
                        
                except Exception as e:
                    logger.error(f"Erro ao processar seção {i+1}: {e}")
        
        # TENTATIVA 3: Se ainda está faltando, tenta extração manual
        if len(todas_as_transacoes) < 70:
            await message.edit_text("🔍 Verificando transações adicionais...")
            transacoes_manuais = extrair_transacoes_manualmente(texto_bruto)
            
            # Combina as transações, evitando duplicatas
            for tm in transacoes_manuais:
                duplicada = False
                for te in todas_as_transacoes:
                    if (te.get('data') == tm.get('data') and 
                        abs(float(te.get('valor', 0)) - float(tm.get('valor', 0))) < 0.01 and
                        te.get('descricao', '')[:20] == tm.get('descricao', '')[:20]):
                        duplicada = True
                        break
                
                if not duplicada:
                    todas_as_transacoes.append(tm)
            
            logger.info(f"Após extração manual: {len(todas_as_transacoes)} transações")
        
        if not todas_as_transacoes:
            await message.edit_text("🤔 A IA não encontrou nenhuma transação válida no extrato.")
            return ConversationHandler.END
        
        # Valida e corrige as transações
        todas_as_transacoes = validar_e_corrigir_transacoes(todas_as_transacoes, texto_bruto)
        
        # Calcula os totais extraídos
        total_entradas_extraido = sum(float(t.get('valor', 0)) for t in todas_as_transacoes if t.get('tipo_transacao') == 'Entrada')
        total_saidas_extraido = sum(float(t.get('valor', 0)) for t in todas_as_transacoes if t.get('tipo_transacao') == 'Saída')
        
        # Verifica se ainda faltam transações
        diferenca_saidas = abs(total_saidas_extraido - total_saidas_real)
        diferenca_entradas = abs(total_entradas_extraido - total_entradas_real)
        
        if diferenca_saidas > 5 or diferenca_entradas > 5:
            logger.info(f"Buscando transações faltantes... Diferença: Entradas={diferenca_entradas:.2f}, Saídas={diferenca_saidas:.2f}")
            
            # Busca transações que podem ter sido perdidas
            transacoes_faltantes = extrair_transacoes_faltantes(texto_bruto, todas_as_transacoes)
            
            if transacoes_faltantes:
                logger.info(f"Encontradas {len(transacoes_faltantes)} transações adicionais")
                todas_as_transacoes.extend(transacoes_faltantes)
                
                # Recalcula os totais
                total_entradas_extraido = sum(float(t.get('valor', 0)) for t in todas_as_transacoes if t.get('tipo_transacao') == 'Entrada')
                total_saidas_extraido = sum(float(t.get('valor', 0)) for t in todas_as_transacoes if t.get('tipo_transacao') == 'Saída')
        
        # Debug para encontrar diferenças
        if diferenca_saidas > 1 or diferenca_entradas > 1:
            debug_diferenca_valores(todas_as_transacoes, total_saidas_real, 'Saída')
            debug_diferenca_valores(todas_as_transacoes, total_entradas_real, 'Entrada')
        
        logger.info(f"""
        Resumo final da extração:
        - Transações encontradas: {len(todas_as_transacoes)}
        - Total entradas extraído: R$ {total_entradas_extraido:.2f} (real: R$ {total_entradas_real:.2f})
        - Total saídas extraído: R$ {total_saidas_extraido:.2f} (real: R$ {total_saidas_real:.2f})
        - Diferença entradas: R$ {abs(total_entradas_extraido - total_entradas_real):.2f}
        - Diferença saídas: R$ {abs(total_saidas_extraido - total_saidas_real):.2f}
        """)
        
        # Armazena o resultado final
        context.user_data['dados_extrato'] = {"transacoes": todas_as_transacoes}
        
        # IMPORTANTE: Armazena os totais REAIS do extrato, não os calculados
        context.user_data['totais_reais'] = {
            'entradas': total_entradas_real,
            'saidas': total_saidas_real
        }
        
        # Pergunta a qual conta associar
        await mostrar_selecao_conta(update, message, len(todas_as_transacoes))
        return AWAIT_CONTA_ASSOCIADA
        
    except Exception as e:
        logger.error(f"Erro CRÍTICO no processamento do arquivo de extrato: {e}", exc_info=True)
        await message.edit_text("❌ Ops! Ocorreu um erro inesperado ao processar seu arquivo.")
        return ConversationHandler.END
    



def extrair_transacoes_manualmente(texto: str) -> List[Dict]:
    """
    Extração manual de transações como fallback quando a IA falha.
    Corrigido para múltiplos bancos com padrões mais robustos.
    """
    transacoes = []
    
    # Padrões específicos para diferentes bancos
    padroes_nubank = [
        (r'Transferência (enviada|recebida) pelo Pix\s+(.+?)\s+([\d.,]+)$', 'transferencia'),
        (r'Pagamento de fatura\s+([\d.,]+)$', 'pagamento'),
        (r'Compra no débito via NuPay\s+(.+?)\s+([\d.,]+)$', 'compra'),
        (r'Valor adicionado.+?\s+([\d.,]+)$', 'deposito'),
        (r'Rendimento líquido\s+([\d.,]+)$', 'rendimento'),
    ]
    
    padroes_genericos = [
        (r'(TRANSFERENCIA|TED|DOC)\s+.*?\s+([\d.,]+)', 'transferencia'),
        (r'(PAGAMENTO|DEBITO)\s+.*?\s+([\d.,]+)', 'pagamento'),
        (r'(DEPOSITO|CREDITO)\s+.*?\s+([\d.,]+)', 'deposito'),
        (r'(SAQUE|RETIRADA)\s+.*?\s+([\d.,]+)', 'saque'),
        (r'(COMPRA)\s+.*?\s+([\d.,]+)', 'compra'),
    ]
    
    # Combina todos os padrões
    todos_padroes = padroes_nubank + padroes_genericos
    
    # Padrões de data diferentes
    padroes_data = [
        re.compile(r'^(\d{1,2}\s+(JAN|FEV|MAR|ABR|MAI|JUN|JUL|AGO|SET|OUT|NOV|DEZ)\s+\d{4})'),  # Nubank
        re.compile(r'^(\d{1,2}[/\-]\d{1,2}[/\-]\d{4})'),  # DD/MM/YYYY ou DD-MM-YYYY
        re.compile(r'^(\d{4}[/\-]\d{1,2}[/\-]\d{1,2})'),  # YYYY/MM/DD ou YYYY-MM-DD
    ]
    
    linhas = texto.split('\n')
    data_atual = None
    ano_atual = datetime.now().year
    
    meses = {
        'JAN': '01', 'FEV': '02', 'MAR': '03', 'ABR': '04',
        'MAI': '05', 'JUN': '06', 'JUL': '07', 'AGO': '08',
        'SET': '09', 'OUT': '10', 'NOV': '11', 'DEZ': '12'
    }
    
    # Linhas para ignorar (resumos, totais, etc.)
    ignorar_padroes = [
        'Saldo inicial', 'Saldo final', 'Total de entradas', 'Total de saídas', 
        'Rendimento líquido total', 'Período:', 'EXTRATO', 'CONTA',
        'Agência:', 'Titular:', 'CPF:', 'Página'
    ]
    
    vistos = set()  # Para evitar duplicatas
    
    logger.info(f"Iniciando extração manual de {len(linhas)} linhas")
    
    for num_linha, linha in enumerate(linhas):
        linha = linha.strip()
        if not linha or len(linha) < 5:
            continue
            
        # Pula linhas de resumo/cabeçalho
        if any(padrao in linha for padrao in ignorar_padroes):
            continue
        
        # Tenta detectar data
        data_encontrada = False
        for padrao_data in padroes_data:
            match_data = padrao_data.match(linha)
            if match_data:
                data_str = match_data.group(1)
                
                # Se é formato Nubank (15 JAN 2024)
                if ' ' in data_str and any(mes in data_str for mes in meses.keys()):
                    partes = data_str.split()
                    if len(partes) >= 3:
                        dia = partes[0].zfill(2)
                        mes = meses.get(partes[1], '01')
                        ano = partes[2] if len(partes) > 2 else str(ano_atual)
                        data_atual = f"{dia}/{mes}/{ano}"
                        data_encontrada = True
                        break
                else:
                    # Formato DD/MM/YYYY ou similar
                    data_atual = normalizar_data(data_str)
                    data_encontrada = True
                    break
        
        if data_encontrada:
            continue
        
        # Se não temos data, pula
        if not data_atual:
            continue
        
        # Tenta extrair transação usando os padrões
        for padrao, tipo_operacao in todos_padroes:
            try:
                match = re.search(padrao, linha, re.IGNORECASE)
                if match:
                    grupos = match.groups()
                    
                    # Extrai valor (sempre o último grupo que parece valor)
                    valor_str = None
                    descricao = ""
                    
                    for grupo in reversed(grupos):
                        if re.match(r'[\d.,]+$', grupo):
                            valor_str = grupo
                            break
                    
                    if not valor_str:
                        continue
                    
                    # Converte valor
                    try:
                        valor = float(valor_str.replace('.', '').replace(',', '.'))
                        if valor <= 0:
                            continue
                    except ValueError:
                        continue
                    
                    # Extrai descrição (parte antes do valor)
                    posicao_valor = linha.rfind(valor_str)
                    if posicao_valor > 0:
                        descricao = linha[:posicao_valor].strip()
                    else:
                        descricao = linha.replace(valor_str, '').strip()
                    
                    # Remove caracteres especiais da descrição
                    descricao = re.sub(r'[^\w\s\-\.]', ' ', descricao)
                    descricao = re.sub(r'\s+', ' ', descricao).strip()
                    
                    if len(descricao) < 3:
                        descricao = f"Transação {tipo_operacao}"
                    
                    # Determina tipo de transação
                    tipo_transacao = 'Saída'  # Padrão
                    
                    if any(palavra in linha.lower() for palavra in 
                           ['recebida', 'recebido', 'deposito', 'credito', 'valor adicionado', 'rendimento']):
                        tipo_transacao = 'Entrada'
                    elif 'enviada' in linha.lower() or tipo_operacao in ['pagamento', 'saque', 'compra']:
                        tipo_transacao = 'Saída'
                    
                    # Cria chave única para evitar duplicatas
                    chave = f"{data_atual}_{valor:.2f}_{descricao[:20].lower().replace(' ', '')}"
                    
                    if chave in vistos:
                        continue
                    
                    vistos.add(chave)
                    
                    # Categorização básica
                    categoria, subcategoria = categorizar_transacao_automatica(descricao)
                    
                    transacao = {
                        'data': data_atual,
                        'descricao': descricao[:100],  # Limita tamanho
                        'valor': valor,
                        'tipo_transacao': tipo_transacao,
                        'categoria': categoria,
                        'subcategoria': subcategoria
                    }
                    
                    transacoes.append(transacao)
                    logger.debug(f"Transação extraída: {transacao}")
                    break  # Para no primeiro padrão que der match
                    
            except Exception as e:
                logger.error(f"Erro ao processar linha {num_linha}: {e}")
                continue
    
    logger.info(f"Extração manual concluída: {len(transacoes)} transações encontradas")
    return transacoes    


async def mostrar_selecao_conta(update: Update, message, num_transacoes: int):
    """Mostra opções de conta para associar o extrato."""
    db = next(get_db())
    try:
        user_db = get_or_create_user(db, update.effective_user.id, update.effective_user.full_name)
        contas = db.query(Conta).filter(
            Conta.id_usuario == user_db.id,
            Conta.tipo != 'Cartão de Crédito'
        ).all()

        if not contas:
            await message.edit_text("Você não tem contas cadastradas. Use `/configurar` para adicionar uma.")
            return

        botoes = [[InlineKeyboardButton(c.nome, callback_data=f"extrato_conta_{c.id}")] for c in contas]
        await message.edit_text(
            f"🏦 Análise concluída! Encontrei <b>{num_transacoes}</b> transações.\n\n"
            "A qual das suas contas este extrato pertence?",
            reply_markup=InlineKeyboardMarkup(botoes),
            parse_mode='HTML'
        )
    finally:
        db.close()


async def associar_conta_e_confirmar_extrato(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Mostra o resumo do extrato para confirmação, usando os totais validados.
    """
    query = update.callback_query
    await query.answer()
    
    conta_id = int(query.data.split('_')[-1])
    context.user_data['conta_id_extrato'] = conta_id

    dados_extrato = context.user_data.get('dados_extrato', {})
    transacoes = dados_extrato.get('transacoes', [])
    
    if not transacoes:
        await query.edit_message_text("Não foram encontradas transações válidas no extrato.")
        return ConversationHandler.END
    
    # CORREÇÃO: Garantir que os valores estão sendo calculados corretamente
    total_entradas = 0.0
    total_saidas = 0.0
    
    # Log para debug das transações
    logger.info(f"Iniciando cálculo de totais para {len(transacoes)} transações")
    
    # Calcula manualmente os totais para garantir precisão
    for i, t in enumerate(transacoes):
        try:
            # Garante que o valor seja numérico
            valor_raw = t.get('valor', 0)
            if isinstance(valor_raw, str):
                # Remove formatação monetária se presente
                valor_raw = re.sub(r'[R$\s]', '', valor_raw)
                valor_raw = valor_raw.replace('.', '').replace(',', '.')
            
            valor = float(valor_raw)
            tipo = t.get('tipo_transacao', '').strip()
            
            # Log de cada transação para debug
            logger.debug(f"Transação {i+1}: valor={valor}, tipo='{tipo}', desc='{t.get('descricao', '')[:30]}'")
            
            # Classificação mais rigorosa do tipo
            if tipo == 'Entrada':
                total_entradas += valor
            elif tipo == 'Saída':
                total_saidas += valor
            else:
                # Se o tipo não estiver definido, tenta inferir pela descrição
                desc = t.get('descricao', '').lower()
                if any(palavra in desc for palavra in ['recebida', 'recebido', 'deposito', 'credito', 'transferencia recebida', 'valor adicionado']):
                    total_entradas += valor
                    # Atualiza o tipo na transação para consistência
                    t['tipo_transacao'] = 'Entrada'
                    logger.debug(f"  -> Classificado como Entrada pela descrição")
                else:
                    total_saidas += valor
                    # Atualiza o tipo na transação para consistência
                    t['tipo_transacao'] = 'Saída'
                    logger.debug(f"  -> Classificado como Saída pela descrição")
                    
        except (ValueError, TypeError) as e:
            logger.warning(f"Erro ao processar valor da transação {i+1}: {e}. Dados: {t}")
            continue
    
    # Log dos totais calculados
    logger.info(f"Totais calculados: Entradas=R$ {total_entradas:.2f}, Saídas=R$ {total_saidas:.2f}")
    
    # Verifica se há totais REAIS extraídos do extrato original (mais confiáveis)
    totais_reais = context.user_data.get('totais_reais', {})
    
    if totais_reais:
        total_entradas_real = totais_reais.get('entradas', 0.0)
        total_saidas_real = totais_reais.get('saidas', 0.0)
        
        logger.info(f"Totais reais do extrato: Entradas=R$ {total_entradas_real:.2f}, Saídas=R$ {total_saidas_real:.2f}")
        
        # Se há uma diferença significativa, usa os valores reais do extrato
        diferenca_entradas = abs(total_entradas - total_entradas_real)
        diferenca_saidas = abs(total_saidas - total_saidas_real)
        
        if diferenca_entradas > 5.0:
            logger.warning(f"Diferença significativa nas entradas: calculado={total_entradas:.2f}, real={total_entradas_real:.2f}. Usando valor real.")
            total_entradas = total_entradas_real
            
        if diferenca_saidas > 5.0:
            logger.warning(f"Diferença significativa nas saídas: calculado={total_saidas:.2f}, real={total_saidas_real:.2f}. Usando valor real.")
            total_saidas = total_saidas_real
    
    # Monta a prévia das transações
    lista_transacoes_str = []
    for t in transacoes[:10]:  # Mostra apenas as primeiras 10 para não poluir
        emoji = "🟢" if t.get('tipo_transacao') == 'Entrada' else "🔴"
        data_str = t.get('data', 'N/D')
        desc = t.get('descricao', 'N/A')
        valor = float(t.get('valor', 0.0))
        lista_transacoes_str.append(f"{emoji} <code>{data_str}</code> - {desc[:30]:<30} <b>R$ {valor:>7.2f}</b>")

    # Deleta a mensagem anterior
    await query.message.delete()

    # Envia a lista resumida
    if len(transacoes) > 10:
        cabecalho = f"<b>Revisão das Transações (mostrando 10 de {len(transacoes)}):</b>\n\n"
    else:
        cabecalho = "<b>Revisão das Transações Encontradas:</b>\n\n"
    
    corpo_lista = "\n".join(lista_transacoes_str)
    await enviar_texto_em_blocos(context.bot, update.effective_chat.id, cabecalho + corpo_lista)

    # Envia a mensagem final de confirmação com os totais CORRETOS
    texto_confirmacao = (
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<b>Resumo da Importação:</b>\n"
        f"📄 Transações encontradas: <b>{len(transacoes)}</b>\n"
        f"🟢 Total de Entradas: <code>R$ {total_entradas:.2f}</code>\n"
        f"🔴 Total de Saídas: <code>R$ {total_saidas:.2f}</code>\n"
        f"💰 Saldo do Período: <code>R$ {(total_entradas - total_saidas):.2f}</code>\n\n"
        "Deseja importar todas essas movimentações para a conta selecionada?"
    )
    
    # Log para debug
    logger.info(f"""
    Totais finais:
    - Transações: {len(transacoes)}
    - Entradas: R$ {total_entradas:.2f}
    - Saídas: R$ {total_saidas:.2f}
    - Saldo: R$ {(total_entradas - total_saidas):.2f}
    """)
    
    keyboard = [
        [InlineKeyboardButton("✅ Sim, importar tudo", callback_data="extrato_confirm_save")],
        [InlineKeyboardButton("❌ Cancelar", callback_data="extrato_confirm_cancel")]
    ]
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=texto_confirmacao,
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return AWAIT_CONFIRMATION

# --- SALVAR TRANSACOES E CANCELAR ---

async def salvar_transacoes_extrato_em_lote(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Salva as transações extraídas em lote na conta associada.
    """
    query = update.callback_query
    await query.answer()
    
    conta_id = context.user_data.get('conta_id_extrato')
    dados_extrato = context.user_data.get('dados_extrato', {})
    transacoes = dados_extrato.get('transacoes', [])
    
    if not conta_id or not transacoes:
        await query.edit_message_text("Dados insuficientes para salvar as transações.")
        return ConversationHandler.END
    
    # Salva as transações na base
    db: Session = next(get_db())
    try:
        usuario = get_or_create_user(db, update.effective_user.id, update.effective_user.full_name)
        conta = db.query(Conta).filter(Conta.id == conta_id, Conta.id_usuario == usuario.id).first()
        
        if not conta:
            await query.edit_message_text("Conta não encontrada. Se o problema persistir, entre em contato com o suporte.")
            return ConversationHandler.END
        
        # Salva cada transação
        for transacao in transacoes:
            try:
                # Mapeia o tipo_transacao para o campo 'tipo' do modelo
                tipo_mapped = transacao.get('tipo_transacao', 'Saída')
                if tipo_mapped == 'Entrada':
                    tipo_db = 'Entrada'
                else:
                    tipo_db = 'Saída'
                
                # Busca categoria e subcategoria se fornecidas
                id_categoria = None
                id_subcategoria = None
                
                categoria_nome = transacao.get('categoria_sugerida') or transacao.get('categoria')
                subcategoria_nome = transacao.get('subcategoria_sugerida') or transacao.get('subcategoria')
                
                if categoria_nome:
                    categoria_obj = db.query(Categoria).filter(Categoria.nome.ilike(f"%{categoria_nome}%")).first()
                    if categoria_obj:
                        id_categoria = categoria_obj.id
                        
                        if subcategoria_nome:
                            subcategoria_obj = db.query(Subcategoria).filter(
                                Subcategoria.nome.ilike(f"%{subcategoria_nome}%"),
                                Subcategoria.id_categoria == categoria_obj.id
                            ).first()
                            if subcategoria_obj:
                                id_subcategoria = subcategoria_obj.id
                
                nova_transacao = Lancamento(
                    id_conta=conta.id,
                    id_usuario=usuario.id,
                    data_transacao=datetime.strptime(transacao['data'], '%d/%m/%Y'),
                    descricao=transacao['descricao'],
                    valor=float(transacao['valor']),
                    tipo=tipo_db,
                    forma_pagamento=conta.nome,  # Nome da conta como forma de pagamento
                    id_categoria=id_categoria,
                    id_subcategoria=id_subcategoria
                )
                
                db.add(nova_transacao)
            except Exception as e:
                logger.error(f"Erro ao salvar transação {transacao}: {e}", exc_info=True)
        
        db.commit()
        await query.edit_message_text("✅ Todas as transações foram salvas com sucesso!")
        
        # Limpa os dados do usuário
        context.user_data.pop('dados_extrato', None)
        context.user_data.pop('conta_id_extrato', None)
        context.user_data.pop('totais_reais', None)
        
        # Verifica se é um usuário novo (criado há menos de 5 minutos) para enviar mensagem de boas-vindas
        try:
            if usuario.criado_em.tzinfo is None:
                # Se o datetime do usuário não tem timezone, assume UTC
                usuario_criado_utc = usuario.criado_em.replace(tzinfo=timezone.utc)
            else:
                usuario_criado_utc = usuario.criado_em
            
            is_new_user = (datetime.now(timezone.utc) - usuario_criado_utc).total_seconds() < 300
        except Exception:
            # Se houver erro na comparação, assume que não é usuário novo
            is_new_user = False
        
        if is_new_user:
            await query.message.reply_html(
                "🎉 Bem-vindo ao nosso sistema de gestão financeira!\n\n"
                "Agora você pode acompanhar suas despesas, receitas e muito mais.\n"
                "Explore as funcionalidades e aproveite ao máximo seu controle financeiro."
            )
        
    except Exception as e:
        logger.error(f"Erro ao salvar transações em lote: {e}", exc_info=True)
        await query.edit_message_text("❌ Ocorreu um erro ao salvar suas transações. Tente novamente mais tarde.")
    
    finally:
        db.close()
    
    return ConversationHandler.END


async def cancelar_confirmacao_extrato(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Cancela a confirmação do extrato e retorna ao estado anterior.
    """
    query = update.callback_query
    await query.answer()
    
    # Restaura os dados do usuário, se disponíveis
    dados_extrato = context.user_data.get('dados_extrato')
    if dados_extrato:
        transacoes = dados_extrato.get('transacoes', [])
        await mostrar_selecao_conta(update, query.message, len(transacoes))
    else:
        await query.edit_message_text("Operação cancelada. Você pode enviar um novo extrato a qualquer momento.")
    
    return ConversationHandler.END

# --- FLUXO PRINCIPAL E HANDLERS ---

# Mover as funções salvar_transacoes_extrato_em_lote e cancelar_confirmacao_extrato para antes de criar_conversation_handler_extrato
# (Elimine qualquer 'pass' deixado por engano)

# --- HANDLER PRINCIPAL ---
def criar_conversation_handler_extrato():
    """Cria e retorna o ConversationHandler para análise de extratos."""
    return ConversationHandler(
        entry_points=[CommandHandler('extrato', extrato_start)],
        states={
            AWAIT_EXTRATO_FILE: [
                MessageHandler(filters.Document.ALL, processar_extrato_arquivo)
            ],
            AWAIT_CONTA_ASSOCIADA: [
                CallbackQueryHandler(associar_conta_e_confirmar_extrato, 
                    pattern=r'^extrato_conta_\d+$'
                )
            ],
            AWAIT_CONFIRMATION: [
                CallbackQueryHandler(
                    salvar_transacoes_extrato_em_lote,
                    pattern='^extrato_confirm_save$'
                ),
                CallbackQueryHandler(
                    cancelar_confirmacao_extrato,
                    pattern='^extrato_confirm_cancel$'
                )
            ]
        },
        fallbacks=[
            CommandHandler('cancel', cancel),
            MessageHandler(filters.TEXT & filters.Regex(r'^/cancel$'), cancel)
        ],
        name="extrato_conversation",
        persistent=False
    )


# --- FUNÇÕES AUXILIARES ---

def extrair_periodo_extrato(texto: str) -> Tuple[str, str]:
    """Extrai o período do extrato (data inicial e final)."""
    # Padrão comum: "Período: 01/01/2024 a 31/01/2024"
    padrao_periodo = r'Período[:\s]+(\d{1,2}[/\-]\d{1,2}[/\-]\d{4})\s+a\s+(\d{1,2}[/\-]\d{1,2}[/\-]\d{4})'
    match = re.search(padrao_periodo, texto, re.IGNORECASE)
    
    if match:
        return match.group(1), match.group(2)
    
    # Padrão alternativo: busca primeira e última data no texto
    datas = re.findall(r'\d{1,2}[/\-]\d{1,2}[/\-]\d{4}', texto)
    if len(datas) >= 2:
        return datas[0], datas[-1]
    
    return "", ""


def detectar_banco_extrato(texto: str) -> str:
    """Detecta qual banco gerou o extrato baseado em padrões no texto."""
    texto_upper = texto.upper()
    
    if 'NUBANK' in texto_upper:
        return 'Nubank'
    elif 'ITAU' in texto_upper or 'ITAÚ' in texto_upper:
        return 'Itaú'
    elif 'BRADESCO' in texto_upper:
        return 'Bradesco'
    elif 'SANTANDER' in texto_upper:
        return 'Santander'
    elif 'BANCO DO BRASIL' in texto_upper or 'BB' in texto_upper:
        return 'Banco do Brasil'
    elif 'CAIXA' in texto_upper:
        return 'Caixa Econômica'
    elif 'INTER' in texto_upper:
        return 'Inter'
    elif 'C6' in texto_upper:
        return 'C6 Bank'
    elif 'PAN' in texto_upper:
        return 'Banco Pan'
    elif 'XP' in texto_upper:
        return 'XP Investimentos'
    else:
        return 'Banco não identificado'


def validar_formato_data(data_str: str) -> bool:
    """Valida se a string está em formato de data válido."""
    padroes_data = [
        r'^\d{1,2}[/\-]\d{1,2}[/\-]\d{4}$',  # DD/MM/YYYY ou DD-MM-YYYY
        r'^\d{4}[/\-]\d{1,2}[/\-]\d{1,2}$',  # YYYY/MM/DD ou YYYY-MM-DD
        r'^\d{1,2}[/\-]\d{1,2}[/\-]\d{2}$',  # DD/MM/YY ou DD-MM-YY
    ]
    
    for padrao in padroes_data:
        if re.match(padrao, data_str):
            return True
    return False


def normalizar_data(data_str: str) -> str:
    """Normaliza diferentes formatos de data para DD/MM/YYYY."""
    if not data_str:
        return ""
    
    # Remove espaços
    data_str = data_str.strip()
    
    # Se já está no formato DD/MM/YYYY, retorna como está
    if re.match(r'^\d{1,2}/\d{1,2}/\d{4}$', data_str):
        return data_str
    
    # Converte outros formatos
    try:
        # Tenta diferentes formatos
        formatos = ['%d/%m/%Y', '%d-%m-%Y', '%Y/%m/%d', '%Y-%m-%d', '%d/%m/%y', '%d-%m-%y']
        
        for formato in formatos:
            try:
                data_obj = datetime.strptime(data_str, formato)
                return data_obj.strftime('%d/%m/%Y')
            except ValueError:
                continue
        
        # Se nenhum formato funcionou, retorna string original
        return data_str
        
    except Exception:
        return data_str


def extrair_valor_monetario(texto: str) -> float:
    """Extrai valor monetário de uma string."""
    # Remove espaços e converte para uppercase
    texto = texto.strip().upper()
    
    # Padrões comuns para valores monetários
    padroes = [
        r'R\$\s*([\d.,]+)',  # R$ 1.234,56
        r'([\d.,]+)\s*R\$',  # 1.234,56 R$
        r'([\d.,]+)',        # 1.234,56
    ]
    
    for padrao in padroes:
        match = re.search(padrao, texto)
        if match:
            valor_str = match.group(1)
            try:
                # Remove pontos de milhares e converte vírgula para ponto
                if ',' in valor_str and '.' in valor_str:
                    # Formato: 1.234,56
                    valor_str = valor_str.replace('.', '').replace(',', '.')
                elif ',' in valor_str:
                    # Formato: 1234,56
                    valor_str = valor_str.replace(',', '.')
                
                return float(valor_str)
            except ValueError:
                continue
    
    return 0.0


def categorizar_transacao_automatica(descricao: str) -> Tuple[str, str]:
    """Categoriza transação automaticamente baseada na descrição."""
    descricao_upper = descricao.upper()
    
    # Mapeamento de palavras-chave para categorias
    mapeamento = {
        # Alimentação
        ('ALIMENTACAO', 'RESTAURANTE'): ('SUPERMERCADO', 'MERCADO', 'PADARIA', 'LANCHONETE', 'PIZZARIA', 'HAMBURGER', 'IFOOD', 'RAPPI', 'UBER EATS'),
        
        # Transporte
        ('TRANSPORTE', 'COMBUSTIVEL'): ('POSTO', 'GASOLINA', 'UBER', '99', 'METRO', 'ONIBUS', 'TAXI', 'ESTACIONAMENTO'),
        
        # Moradia
        ('MORADIA', 'ALUGUEL'): ('ALUGUEL', 'CONDOMINIO', 'IPTU', 'ENERGIA', 'AGUA', 'GAS', 'INTERNET', 'TELEFONE'),
        
        # Saúde
        ('SAUDE', 'CONSULTA'): ('HOSPITAL', 'CLINICA', 'FARMACIA', 'DROGARIA', 'MEDICO', 'DENTISTA', 'EXAME'),
        
        # Educação
        ('EDUCACAO', 'CURSO'): ('ESCOLA', 'FACULDADE', 'UNIVERSIDADE', 'CURSO', 'LIVRO', 'MATERIAL ESCOLAR'),
        
        # Lazer
        ('LAZER', 'ENTRETENIMENTO'): ('CINEMA', 'TEATRO', 'SHOW', 'SPOTIFY', 'NETFLIX', 'AMAZON PRIME', 'YOUTUBE'),
        
        # Vestuário
        ('VESTUARIO', 'ROUPA'): ('LOJA', 'ROUPA', 'SAPATO', 'CALCA', 'CAMISA', 'VESTIDO', 'ZARA', 'RENNER'),
        
        # Receitas
        ('RECEITA', 'SALARIO'): ('SALARIO', 'TRANSFERENCIA', 'PIX RECEBIDO', 'DEPOSITO', 'RENDIMENTO'),
    }
    
    # Verifica cada categoria
    for (categoria, subcategoria), palavras_chave in mapeamento.items():
        for palavra in palavras_chave:
            if palavra in descricao_upper:
                return categoria, subcategoria
    
    # Categoria padrão
    return 'OUTROS', 'GERAL'


def extrair_transacoes_faltantes(texto: str, transacoes_existentes: List[Dict]) -> List[Dict]:
    """
    Busca transações que podem ter sido perdidas pela IA, usando padrões comuns de extratos.
    Retorna apenas transações que não estão em transacoes_existentes.
    """
    transacoes_adicionais = []
    
    # Cria conjunto de chaves das transações existentes para comparação rápida
    chaves_existentes = set()
    for t in transacoes_existentes:
        data = t.get('data', '')
        valor = float(t.get('valor', 0))
        desc_inicio = t.get('descricao', '')[:20].lower().replace(' ', '')
        chave = f"{data}_{valor:.2f}_{desc_inicio}"
        chaves_existentes.add(chave)
    
    # Padrões mais abrangentes para diferentes tipos de bancos
    padroes = [
        # Nubank
        (r'Transferência (enviada|recebida) pelo Pix\s+(.+?)\s+([\d.,]+)$', 'pix'),
        (r'Pagamento de fatura\s+([\d.,]+)$', 'pagamento'),
        (r'Compra no débito via NuPay\s+(.+?)\s+([\d.,]+)$', 'compra'),
        (r'Valor adicionado.+?\s+([\d.,]+)$', 'deposito'),
        
        # Padrões genéricos
        (r'(TED|DOC|TRANSFERENCIA)\s+.*?\s+([\d.,]+)', 'transferencia'),
        (r'(DEBITO|PAGTO|PAGAMENTO)\s+.*?\s+([\d.,]+)', 'pagamento'),
        (r'(SAQUE|ATM)\s+.*?\s+([\d.,]+)', 'saque'),
        (r'(DEPOSITO|CREDITO)\s+.*?\s+([\d.,]+)', 'deposito'),
        (r'(COMPRA|CARTAO)\s+.*?\s+([\d.,]+)', 'compra'),
    ]
    
    # Padrão para detectar datas
    padrao_data = re.compile(r'^(\d{1,2}\s+(JAN|FEV|MAR|ABR|MAI|JUN|JUL|AGO|SET|OUT|NOV|DEZ)\s+\d{4})')
    
    linhas = texto.split('\n')
    data_atual = None
    
    meses = {
        'JAN': '01', 'FEV': '02', 'MAR': '03', 'ABR': '04',
        'MAI': '05', 'JUN': '06', 'JUL': '07', 'AGO': '08',
        'SET': '09', 'OUT': '10', 'NOV': '11', 'DEZ': '12'
    }
    
    # Linhas para ignorar
    ignorar_padroes = [
        'Saldo inicial', 'Saldo final', 'Total de entradas', 'Total de saídas', 
        'Rendimento líquido total', 'Período:', 'EXTRATO'
    ]
    
    for linha in linhas:
        linha = linha.strip()
        if not linha or any(padrao in linha for padrao in ignorar_padroes):
            continue
        
        # Detecta data
        match_data = padrao_data.match(linha)
        if match_data:
            partes = match_data.group(1).split()
            if len(partes) >= 3:
                dia = partes[0].zfill(2)
                mes = meses.get(partes[1], '01')
                ano = partes[2]
                data_atual = f"{dia}/{mes}/{ano}"
            continue
        
        if not data_atual:
            continue
        
        # Tenta extrair transação com cada padrão
        for padrao, tipo_operacao in padroes:
            try:
                match = re.search(padrao, linha, re.IGNORECASE)
                if match:
                    grupos = match.groups()
                    
                    # Identifica o valor (último grupo numérico)
                    valor_str = None
                    for grupo in reversed(grupos):
                        if re.match(r'[\d.,]+$', grupo):
                            valor_str = grupo
                            break
                    
                    if not valor_str:
                        continue
                    
                    # Converte valor
                    try:
                        valor = float(valor_str.replace('.', '').replace(',', '.'))
                        if valor <= 0:
                            continue
                    except ValueError:
                        continue
                    
                    # Extrai descrição
                    posicao_valor = linha.rfind(valor_str)
                    if posicao_valor > 0:
                        descricao = linha[:posicao_valor].strip()
                    else:
                        descricao = linha.replace(valor_str, '').strip()
                    
                    # Limpa descrição
                    descricao = re.sub(r'[^\w\s\-\.]', ' ', descricao)
                    descricao = re.sub(r'\s+', ' ', descricao).strip()[:80]
                    
                    if len(descricao) < 3:
                        descricao = f"Transação {tipo_operacao}"
                    
                    # Determina tipo
                    tipo_transacao = 'Saída'
                    if any(palavra in linha.lower() for palavra in 
                           ['recebida', 'recebido', 'deposito', 'credito', 'valor adicionado']):
                        tipo_transacao = 'Entrada'
                    
                    # Verifica se já existe
                    desc_inicio = descricao[:20].lower().replace(' ', '')
                    chave = f"{data_atual}_{valor:.2f}_{desc_inicio}"
                    
                    if chave in chaves_existentes:
                        continue
                    
                    # Adiciona à lista
                    categoria, subcategoria = categorizar_transacao_automatica(descricao)
                    
                    transacao = {
                        'data': data_atual,
                        'descricao': descricao,
                        'valor': valor,
                        'tipo_transacao': tipo_transacao,
                        'categoria': categoria,
                        'subcategoria': subcategoria
                    }
                    
                    transacoes_adicionais.append(transacao)
                    chaves_existentes.add(chave)  # Evita duplicatas internas
                    break  # Para no primeiro padrão que der match
                    
            except Exception as e:
                logger.error(f"Erro ao processar linha para transações faltantes: {e}")
                continue
    
    logger.info(f"Encontradas {len(transacoes_adicionais)} transações adicionais")
    return transacoes_adicionais


def debug_diferenca_valores(transacoes: List[Dict], total_real: float, tipo: str, arquivo_debug: str = None):
    """
    Salva as diferenças entre o total extraído e o total real, além das transações do tipo especificado, em um arquivo JSON para debugging.
    """
    if arquivo_debug is None:
        arquivo_debug = f"debug_diferenca_{tipo.lower()}.json"
    try:
        transacoes_tipo = [t for t in transacoes if isinstance(t, dict) and t.get('tipo_transacao') == tipo]
        total_extraido = sum(float(t.get('valor', 0)) for t in transacoes_tipo)
        debug_info = {
            'tipo': tipo,
            'total_real': total_real,
            'total_extraido': total_extraido,
            'diferenca': abs(total_real - total_extraido),
            'transacoes': transacoes_tipo
        }
        with open(arquivo_debug, 'w', encoding='utf-8') as f:
            json.dump(debug_info, f, indent=2, ensure_ascii=False, default=str)
        logger.info(f"Arquivo de debug salvo: {arquivo_debug}")
    except Exception as e:
        logger.error(f"Erro ao salvar debug de diferença de valores: {e}")


def validar_e_corrigir_transacoes(transacoes: List[Dict], texto_extrato: str) -> List[Dict]:
    """
    Valida e corrige as transações extraídas comparando com o texto original.
    Aplica deduplicação robusta e salva debug se houver diferença.
    """
    # Filtra transações inválidas ou None
    transacoes = [t for t in transacoes if isinstance(t, dict) and t.get('data') and t.get('valor') is not None and t.get('descricao')]
    # Deduplicação robusta
    transacoes_unicas = []
    vistos = set()
    for t in transacoes:
        try:
            data = t.get('data', '').strip()
            valor = round(float(t.get('valor', 0)), 2)
            desc = t.get('descricao', '').strip()[:30].lower()
            chave = f"{data}_{valor}_{desc}"
            if chave not in vistos:
                vistos.add(chave)
                transacoes_unicas.append(t)
            else:
                logger.warning(f"Transação duplicada removida: {chave}")
        except Exception as e:
            logger.warning(f"Transação ignorada por erro de dados: {t} - {e}")
    # Extrai os totais reais do extrato
    match_entradas = re.search(r'Total de entradas\s*\+?\s*([\d.,]+)', texto_extrato)
    match_saidas = re.search(r'Total de saídas\s*-?\s*([\d.,]+)', texto_extrato)
    total_entradas_real = float(match_entradas.group(1).replace('.', '').replace(',', '.')) if match_entradas else 0.0
    total_saidas_real = float(match_saidas.group(1).replace('.', '').replace(',', '.')) if match_saidas else 0.0
    # Calcula os totais das transações extraídas
    total_entradas_calc = sum(float(t.get('valor', 0)) for t in transacoes_unicas if t.get('tipo_transacao') == 'Entrada')
    total_saidas_calc = sum(float(t.get('valor', 0)) for t in transacoes_unicas if t.get('tipo_transacao') == 'Saída')
    logger.info(f"""
    Validação de totais após deduplicação:
    - Entradas: Real={total_entradas_real:.2f}, Calculado={total_entradas_calc:.2f}
    - Saídas: Real={total_saidas_real:.2f}, Calculado={total_saidas_calc:.2f}
    """)
    # Se houver diferença relevante, salva debug
    if abs(total_entradas_calc - total_entradas_real) > 1:
        debug_diferenca_valores(transacoes_unicas, total_entradas_real, 'Entrada')
    if abs(total_saidas_calc - total_saidas_real) > 1:
        debug_diferenca_valores(transacoes_unicas, total_saidas_real, 'Saída')
    return transacoes_unicas

def comparar_extrato_com_pdf(pdf_path: str, debug_json_path: str, tipo: str = 'Saída'):
    """
    Compara os valores extraídos pelo bot (arquivo de debug) com os valores presentes no PDF.
    Gera um relatório de diferenças para facilitar ajuste fino, mostrando lado a lado os valores.
    """
    import fitz  # PyMuPDF
    import json
    import re
    from collections import Counter

    # 1. Extrai texto do PDF
    with fitz.open(pdf_path) as doc:
        texto_pdf = "\n".join(page.get_text() for page in doc)
    # 2. Extrai todos os valores monetários do PDF (com repetição)
    padrao_valor = re.compile(r'([\d\.]+,[\d]{2})')
    valores_pdf = [float(match.replace('.', '').replace(',', '.')) for match in padrao_valor.findall(texto_pdf)]
    valores_pdf_counter = Counter([round(v, 2) for v in valores_pdf])

    # 3. Lê o arquivo de debug
    with open(debug_json_path, 'r', encoding='utf-8') as f:
        debug_data = json.load(f)
    valores_bot = [float(t.get('valor', 0)) for t in debug_data.get('transacoes', [])]
    valores_bot_counter = Counter([round(v, 2) for v in valores_bot])

    # 4. Compara lado a lado
    print(f"\n--- COMPARAÇÃO DETALHADA DE {tipo.upper()} ---")
    print(f"Valores do PDF (com repetição): {sorted(valores_pdf_counter.elements())}")
    print(f"Valores do BOT (com repetição): {sorted(valores_bot_counter.elements())}")

    # Mostra diferenças detalhadas
    faltando = list((valores_pdf_counter - valores_bot_counter).elements())
    sobrando = list((valores_bot_counter - valores_pdf_counter).elements())
    print(f"\nValores no PDF e NÃO no bot: {faltando}")
    print(f"Valores no bot e NÃO no PDF: {sobrando}")
    print(f"Total no PDF: {sum(valores_pdf_counter.elements()):.2f} | Total no bot: {sum(valores_bot_counter.elements()):.2f}")
    print(f"Diferença total: {abs(sum(valores_pdf_counter.elements()) - sum(valores_bot_counter.elements())):.2f}")
    return faltando, sobrando

# --- EXPORTS ---
__all__ = [
    'ProcessadorDeDocumentos',
    'ExtratoValidator',
    'extrato_start',
    'processar_extrato_arquivo',
    'mostrar_selecao_conta',
    'associar_conta_e_confirmar_extrato',
    'salvar_transacoes_extrato_em_lote',
    'cancelar_confirmacao_extrato',
    'criar_conversation_handler_extrato',
    'extrair_periodo_extrato',
    'detectar_banco_extrato',
    'validar_formato_data',
    'normalizar_data',
    'extrair_valor_monetario',
    'categorizar_transacao_automatica',
    'debug_transacoes_extraidas',
    'gerar_relatorio_extrato'
]