import json
import logging
import random
import re
from datetime import datetime, timedelta, timezone
from dateutil.relativedelta import relativedelta
from typing import List, Tuple, Dict, Any
import os
from .services import preparar_contexto_financeiro_completo
import google.generativeai as genai
from sqlalchemy.orm import Session, joinedload
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler, CommandHandler, ContextTypes, ConversationHandler,
    MessageHandler, filters
)

# --- IMPORTS DO PROJETO ---

import config
from database.database import get_db, get_or_create_user, buscar_lancamentos_usuario
from models import Categoria, Lancamento, Subcategoria, Usuario, ItemLancamento, Conta
from .prompts import PROMPT_GERENTE_VDM, PROMPT_INSIGHT_FINAL, SUPER_PROMPT_MAESTRO_CONTEXTUAL

# Importando explicitamente as funções de 'services'
from .services import (
    analisar_comportamento_financeiro,
    buscar_lancamentos_com_relacionamentos,
    definir_perfil_investidor,
    detectar_intencao_e_topico,
    obter_dados_externos,
    preparar_contexto_json
)
from . import services


logger = logging.getLogger(__name__)

# --- ESTADOS DAS CONVERSAS ---
# (O resto do seu arquivo continua a partir daqui)
(AWAIT_GERENTE_QUESTION,) = range(1)
(ASK_NAME,) = range(11, 12)
(ASK_OBJETIVO_DESCRICAO, ASK_OBJETIVO_VALOR, ASK_OBJETIVO_PRAZO) = range(100, 103)

# --- CONSTANTES PARA DETECÇÃO DE INTENÇÕES ---
PALAVRAS_LISTA = {
    'lançamentos', 'lancamentos', 'lançamento', 'lancamento', 'transações', 'transacoes', 
    'transacao', 'transação', 'gastos', 'receitas', 'entradas', 'saidas', 'saídas',
    'despesas', 'historico', 'histórico', 'movimentação', 'movimentacao', 'extrato'
}

PALAVRAS_RESUMO = {
    'resumo', 'relatorio', 'relatório', 'balanço', 'balanco', 'situacao', 'situação',
    'status', 'como estou', 'como está', 'como tá', 'como ta', 'panorama'
}

PERGUNTAS_ESPECIFICAS = {
    'quanto': ['gastei', 'gasto', 'recebi', 'tenho', 'sobrou', 'economizei'],
    'onde': ['gastei', 'comprei', 'paguei'],
    'quando': ['foi', 'comprei', 'paguei', 'gastei']
}

# --- PROMPT PARA ANÁLISE DE IMPACTO ---
PROMPT_ANALISE_IMPACTO = """
**TAREFA:** Você é o **Maestro Financeiro**, um assistente de finanças. O usuário pediu uma informação de mercado e agora quer entender o impacto dela.
Seja conciso e direto. Forneça uma análise útil e sugestões práticas.

**NOME DO USUÁRIO:** {user_name}
**PERFIL DE INVESTIDOR:** {perfil_investidor}
**INFORMAÇÃO DE MERCADO:**
{informacao_externa}

**DADOS FINANCEIROS DO USUÁRIO (JSON):**
{contexto_json}

**SUA RESPOSTA:**
Gere uma análise em 2 seções: "Impacto para Seu Perfil" e "Recomendações", usando o perfil do usuário para personalizar a resposta. Use formatação HTML para Telegram (`<b>`, `<i>`, `<code>`).
**NUNCA use a tag <br>. Use quebras de linha normais.**
"""

# --- CLASSES PARA CONTEXTO MELHORADO ---
class ContextoConversa:
    def __init__(self):
        self.historico: List[Dict[str, str]] = []
        self.topicos_recorrentes: Dict[str, int] = {}
        self.ultima_pergunta_tipo: str = ""
        self.dados_cache: Dict[str, Any] = {}
    
    def adicionar_interacao(self, pergunta: str, resposta: str, tipo: str = "geral"):
        self.historico.append({
            'pergunta': pergunta,
            'resposta': resposta[:300],  # Limita o tamanho
            'tipo': tipo,
            'timestamp': datetime.now().isoformat()
        })
        
        if len(self.historico) > 10:
            self.historico = self.historico[-10:]
        
        palavras_chave = self._extrair_palavras_chave(pergunta)
        for palavra in palavras_chave:
            self.topicos_recorrentes[palavra] = self.topicos_recorrentes.get(palavra, 0) + 1
        
        self.ultima_pergunta_tipo = tipo
    
    def _extrair_palavras_chave(self, texto: str) -> List[str]:
        palavras = re.findall(r'\b\w+\b', texto.lower())
        palavras_relevantes = ['uber', 'ifood', 'supermercado', 'lazer', 'restaurante', 
                              'transporte', 'alimentacao', 'alimentação', 'conta', 'salario', 'salário']
        return [p for p in palavras if p in palavras_relevantes or len(p) > 5]
    
    def get_contexto_formatado(self) -> str:
        if not self.historico:
            return ""
        
        contexto = []
        for item in self.historico[-5:]:
            contexto.append(f"Usuário: {item['pergunta']}")
            contexto.append(f"Maestro: {item['resposta']}")
        
        return "\n".join(contexto)
    
    def tem_topico_recorrente(self, topico: str) -> bool:
        return self.topicos_recorrentes.get(topico.lower(), 0) >= 2

class AnalisadorIntencao:
    @staticmethod
    def detectar_tipo_pergunta(pergunta: str) -> str:
        pergunta_lower = pergunta.lower()

        if "maior despesa" in pergunta_lower or "maior gasto" in pergunta_lower:
            return "maior_despesa"
        
        if any(palavra in pergunta_lower for palavra in ['dolar', 'dólar', 'bitcoin', 'btc', 'selic', 'cotacao', 'cotação', 'euro', 'eur']):
            return "dados_externos"
        
        if any(palavra in pergunta_lower for palavra in PALAVRAS_LISTA):
            return "lista_lancamentos"
        
        if any(palavra in pergunta_lower for palavra in PALAVRAS_RESUMO):
            return "resumo_completo"
        
        for interrogativo, verbos in PERGUNTAS_ESPECIFICAS.items():
            if interrogativo in pergunta_lower and any(verbo in pergunta_lower for verbo in verbos):
                return "pergunta_especifica"
        
        if any(palavra in pergunta_lower for palavra in ['oi', 'olá', 'bom dia', 'boa tarde', 'e ai', 'e aí', 'tudo bem', 'blz']):
            return "conversacional"
        
        
        return "analise_geral"
    
    @staticmethod
    def extrair_limite_lista(pergunta: str) -> int:
        match = re.search(r'\b(\d+)\b', pergunta)
        if match:
            return min(int(match.group(1)), 50)
        
        if any(palavra in pergunta.lower() for palavra in ['último', 'ultimo', 'última', 'ultima']):
            return 1
        
        return 10

# --- FUNÇÕES UTILITÁRIAS MELHORADAS ---

async def enviar_texto_em_blocos(bot, chat_id, texto: str, reply_markup=None):
    """
    Envia texto em blocos, com tratamento robusto de HTML malformado
    """
    # Limpeza básica
    texto_limpo = texto.strip().replace('<br>', '\n').replace('<br/>', '\n')
    
    # Remove HTML malformado antes de enviar
    texto_limpo = _limpar_resposta_ia(texto_limpo)
    
    if len(texto_limpo) <= 4096:
        # Tenta enviar com HTML primeiro
        try:
            await bot.send_message(
                chat_id=chat_id, 
                text=texto_limpo, 
                parse_mode="HTML", 
                reply_markup=reply_markup,
                disable_web_page_preview=True
            )
            return
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem HTML: {e}")
            # Fallback: remove todas as tags HTML e envia como texto simples
            try:
                texto_sem_html = re.sub('<[^<]+?>', '', texto_limpo)
                await bot.send_message(
                    chat_id=chat_id, 
                    text=texto_sem_html, 
                    reply_markup=reply_markup,
                    disable_web_page_preview=True
                )
                return
            except Exception as e2:
                logger.error(f"Erro ao enviar mensagem sem HTML: {e2}")
                return
    
    # Para mensagens longas, divide em partes
    partes = []
    while len(texto_limpo) > 0:
        if len(texto_limpo) <= 4096:
            partes.append(texto_limpo)
            break
        
        corte = texto_limpo[:4096].rfind("\n\n")
        if corte == -1: corte = texto_limpo[:4096].rfind("\n")
        if corte == -1: corte = 4096
        
        partes.append(texto_limpo[:corte])
        texto_limpo = texto_limpo[corte:].strip()
    
    for i, parte in enumerate(partes):
        is_last_part = (i == len(partes) - 1)
        try:
            await bot.send_message(
                chat_id=chat_id, 
                text=parte, 
                parse_mode="HTML", 
                reply_markup=reply_markup if is_last_part else None,
                disable_web_page_preview=True
            )
        except Exception as e:
            logger.error(f"Erro ao enviar parte {i}: {e}")
            # Fallback para parte sem HTML
            try:
                parte_sem_html = re.sub('<[^<]+?>', '', parte)
                await bot.send_message(
                    chat_id=chat_id, 
                    text=parte_sem_html,
                    reply_markup=reply_markup if is_last_part else None,
                    disable_web_page_preview=True
                )
            except Exception as e2:
                logger.error(f"Erro fatal ao enviar parte {i}: {e2}")
                # Em último caso, envia mensagem de erro
                if i == 0:  # Só envia erro na primeira tentativa para não spammar
                    await bot.send_message(
                        chat_id=chat_id,
                        text="Ops! Houve um problema na formatação da resposta. Pode tentar novamente?",
                        reply_markup=reply_markup if is_last_part else None
                    )

def parse_action_buttons(text: str) -> tuple[str, InlineKeyboardMarkup | None]:
    match = re.search(r'\[ACTION_BUTTONS:\s*(.*?)\]', text, re.DOTALL | re.IGNORECASE)
    if not match:
        return text, None
    
    clean_text = text[:match.start()].strip()
    button_data_str = match.group(1)
    
    try:
        button_pairs = [pair.strip() for pair in button_data_str.split(';') if pair.strip()]
        keyboard = []
        row = []
        
        for pair in button_pairs:
            parts = pair.split('|')
            if len(parts) == 2:
                button_text, callback_data = parts[0].strip(), parts[1].strip()
                if len(button_text) <= 40:
                    row.append(InlineKeyboardButton(button_text, callback_data=callback_data))
                    if len(row) == 2:
                        keyboard.append(row)
                        row = []
        if row:
            keyboard.append(row)
        
        if keyboard:
            return clean_text, InlineKeyboardMarkup(keyboard)
    
    except Exception as e:
        logger.error(f"Erro ao parsear botões: {e}")
    
    return clean_text, None

def formatar_lancamento_detalhado(lanc: Lancamento) -> str:
    """
    Formata um lançamento no modelo de card limpo e profissional - VERSÃO 2.0
    """
    # Emojis por tipo
    tipo_emoji = "�" if lanc.tipo == 'Entrada' else "�"
    tipo_cor = "🟢" if lanc.tipo == 'Entrada' else "🔴"
    
    # Formatação da data
    data_formatada = lanc.data_transacao.strftime('%d/%m/%Y')
    hora_formatada = lanc.data_transacao.strftime('%H:%M')
    
    # Descrição limpa (máximo 50 caracteres)
    descricao = lanc.descricao or 'Transação'
    if len(descricao) > 50:
        descricao = descricao[:47] + "..."
    
    # Card limpo e profissional
    card = (
        f"{tipo_emoji} <b>{descricao}</b>\n\n"
        f"<b>💰 Valor:</b> <code>R$ {lanc.valor:.2f}</code>\n"
        f"<b>📅 Data:</b> {data_formatada} às {hora_formatada}\n"
        f"<b>📂 Categoria:</b> {lanc.categoria.nome if lanc.categoria else 'Sem categoria'}\n"
        f"<b>💳 Pagamento:</b> {lanc.forma_pagamento or 'Não informado'}\n"
        f"<b>🏷️ Tipo:</b> {tipo_cor} {lanc.tipo}"
    )
    return card

async def handle_lista_lancamentos(chat_id: int, context: ContextTypes.DEFAULT_TYPE, parametros: dict):
    """
    Busca e exibe lançamentos com base nos parâmetros da IA, incluindo data.
    """
    logger.info(f"Executando handle_lista_lancamentos com parâmetros: {parametros}")
    db = next(get_db())
    try:
        # Converte datas de string para objeto datetime, se existirem
        if 'data_inicio' in parametros:
            parametros['data_inicio'] = datetime.strptime(parametros['data_inicio'], '%Y-%m-%d')
        if 'data_fim' in parametros:
            parametros['data_fim'] = datetime.strptime(parametros['data_fim'], '%Y-%m-%d')

        lancamentos = buscar_lancamentos_usuario(telegram_user_id=chat_id, **parametros)
        
        if not lancamentos:
            await context.bot.send_message(chat_id, "🔍 Nenhum lançamento encontrado com esses critérios. Tente outros filtros!")
            return

        # Cabeçalho profissional
        total_valor = sum(float(l.valor) for l in lancamentos)
        sinal = "+" if any(l.tipo == 'Entrada' for l in lancamentos) and len([l for l in lancamentos if l.tipo == 'Entrada']) == len(lancamentos) else ""
        
        cabecalho = (
            f"📋 <b>Seus Lançamentos</b>\n\n"
            f"<b>📊 Resumo:</b>\n"
            f"• <b>Total encontrado:</b> {len(lancamentos)} lançamento(s)\n"
            f"• <b>Valor total:</b> <code>{sinal}R$ {total_valor:.2f}</code>\n\n"
            f"<b>🗂️ Detalhes:</b>\n"
        )
        
        cards_formatados = [formatar_lancamento_detalhado(lanc) for lanc in lancamentos]
        resposta_final = cabecalho + "\n━━━━━━━━━━━━━━━━━━\n\n".join(cards_formatados)

        await enviar_texto_em_blocos(context.bot, chat_id, resposta_final)
    finally:
        db.close()


def criar_teclado_colunas(botoes: list, colunas: int):
    if not botoes: return []
    return [botoes[i:i + colunas] for i in range(0, len(botoes), colunas)]

def obter_contexto_usuario(context: ContextTypes.DEFAULT_TYPE) -> ContextoConversa:
    if 'contexto_conversa' not in context.user_data:
        context.user_data['contexto_conversa'] = ContextoConversa()
    return context.user_data['contexto_conversa']

# --- HANDLER DE START / HELP (ONBOARDING) ---
HELP_TEXTS = {
    "main": (
        "Olá, <b>{user_name}</b>! 👋\n\n"
        "Bem-vindo ao <b>Maestro Financeiro</b>, seu assistente pessoal para dominar suas finanças. "
        "Sou um bot completo, com inteligência artificial, gráficos, relatórios e muito mais.\n\n"
        "Navegue pelas seções abaixo para descobrir tudo que posso fazer por você:"
    ),
    "lancamentos": (
        "<b>📝 Lançamentos e Registros</b>\n\n"
        "A forma mais fácil de manter suas finanças em dia.\n\n"
        "📸  <b>Leitura Automática (OCR)</b>\n"
        "   • Dentro do comando <code>/lancamento</code>, envie uma <b>foto ou PDF</b> de um cupom fiscal e eu extraio os dados para você.\n\n"
        "📄  <code>/fatura</code>\n"  # <-- LINHA ADICIONADA
        "   • Envie o <b>PDF da fatura do seu cartão</b> e eu lanço todas as despesas de uma vez, de forma inteligente!\n\n" # <-- LINHA ADICIONADA
        "⌨️  <code>/lancamento</code>\n"
        "   • Use para registrar uma <b>Entrada</b> ou <b>Saída</b> manualmente através de um guia passo a passo.\n\n"
        "✏️  <code>/editar</code>\n"
        "   • Use para <b>editar ou apagar</b> um lançamento recente ou buscá-lo pelo nome."
    ),
    "analise": (
        "<b>🧠 Análise e Inteligência</b>\n\n"
        "Transforme seus dados em decisões inteligentes.\n\n"
        "💬  <code>/gerente</code>\n"
        "   • Converse comigo em linguagem natural! Sou uma IA avançada que entende suas perguntas sobre finanças, tem memória e te ajuda com insights práticos.\n"
        "     - <i>\"Quanto gastei com iFood este mês?\"</i>\n"
        "     - <i>\"Qual foi minha maior despesa em Lazer?\"</i>\n"
        "     - <i>\"Como está minha situação financeira?\"</i>\n"
        "     - <i>\"Cotação do dólar hoje\"</i>\n\n"
        "📈  <code>/grafico</code>\n"
        "   • Gere gráficos visuais e interativos de despesas, fluxo de caixa e projeções.\n\n"
        "📄  <code>/relatorio</code>\n"
        "   • Gere um <b>relatório profissional em PDF</b> com o resumo completo do seu mês."
    ),
    "planejamento": (
        "<b>🎯 Metas e Agendamentos</b>\n\n"
        "Planeje seu futuro e automatize sua vida financeira.\n\n"
        "🏆  <code>/novameta</code>\n"
        "   • Crie metas de economia (ex: 'Viagem dos Sonhos') e acompanhe seu progresso.\n\n"
        "📊  <code>/metas</code>\n"
        "   • Veja o andamento de todas as suas metas ativas com barras de progresso.\n\n"
        "🗓️  <code>/agendar</code>\n"
        "   • Automatize suas contas! Agende despesas e receitas recorrentes (salário, aluguel) ou parcelamentos. Eu te lembrarei e lançarei tudo automaticamente."
    ),
    "config": (
        "<b>⚙️ Configurações e Ferramentas</b>\n\n"
        "Deixe o bot com a sua cara e gerencie suas preferências.\n\n"
        "👤  <code>/configurar</code>\n"
        "   • Gerencie suas <b>contas</b>, <b>cartões</b>, defina seu <b>perfil de investidor</b> para receber dicas personalizadas e altere o <b>horário dos lembretes</b>.\n\n"
        "🚨  <code>/alerta [valor]</code>\n"
        "   • Defina um limite de gastos mensal (ex: <code>/alerta 1500</code>). Eu te avisarei se você ultrapassar esse valor.\n\n"
        "💬  <code>/contato</code>\n" 
        "   • Fale com o desenvolvedor! Envie <b>sugestões</b>, <b>dúvidas</b> ou me pague um <b>café via PIX</b> para apoiar o projeto.\n\n"
        "🗑️  <code>/apagartudo</code>\n"
        "   • <b>Exclui permanentemente todos os seus dados</b> do bot. Use com extrema cautela!\n\n"
        "↩️  <code>/cancelar</code>\n"
        "   • Use a qualquer momento para interromper uma operação em andamento."
    ),
    "ml": (
        "<b>🧠 Machine Learning (NOVO!)</b>\n\n"
        "Análise financeira avançada com Inteligência Artificial.\n\n"
        "🤖  <code>/ml</code>\n"
        "   • <b>Análise completa com Machine Learning</b> - Score de saúde, anomalias, previsões e padrões comportamentais.\n\n"
        "🔮  <code>/previsao [meses]</code>\n"
        "   • <b>Prevê seus gastos futuros</b> usando algoritmos avançados (ex: <code>/previsao 6</code>).\n\n"
        "⚠️  <code>/anomalias</code>\n"
        "   • <b>Detecta gastos suspeitos</b> e fora do seu padrão normal usando Isolation Forest.\n\n"
        "🎯  <code>/clusters</code>\n"
        "   • <b>Analisa seus padrões de comportamento</b> financeiro e agrupa gastos similares.\n\n"
        "🤖  <code>/treinar</code>\n"
        "   • <b>Treina um modelo personalizado</b> para classificar automaticamente suas transações futuras.\n\n"
        "<i>💡 Dica: Use /treinar primeiro para melhorar a precisão de todas as análises!</i>"
    )
}

def get_help_keyboard(current_section: str = "main") -> InlineKeyboardMarkup:
    """
    Gera o teclado de navegação interativo para o menu de ajuda.
    Os botões são dispostos de forma inteligente para melhor visualização.
    """
    keyboard = [
        [
            InlineKeyboardButton("📝 Lançamentos", callback_data="help_lancamentos"),
            InlineKeyboardButton("🧠 Análise", callback_data="help_analise"),
        ],
        [
            InlineKeyboardButton("🎯 Planejamento", callback_data="help_planejamento"),
            InlineKeyboardButton("⚙️ Ferramentas", callback_data="help_config"),
        ],
        [
            InlineKeyboardButton("🤖 Machine Learning", callback_data="help_ml"),
        ]
    ]
    
    # Adiciona o botão de "Voltar" apenas se não estivermos no menu principal
    if current_section != "main":
        keyboard.append([InlineKeyboardButton("↩️ Voltar ao Menu Principal", callback_data="help_main")])
    
    return InlineKeyboardMarkup(keyboard)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Envia a mensagem de ajuda principal e interativa ao receber o comando /help.
    Busca o nome do usuário para uma saudação personalizada.
    """
    user = update.effective_user
    db = next(get_db())
    try:
        # Busca o nome do usuário no banco para personalizar a mensagem
        usuario_db = db.query(Usuario).filter(Usuario.telegram_id == user.id).first()
        # Se não encontrar no DB, usa o nome do Telegram como fallback
        user_name = usuario_db.nome_completo.split(' ')[0] if usuario_db and usuario_db.nome_completo else user.first_name
        
        text = HELP_TEXTS["main"].format(user_name=user_name)
        keyboard = get_help_keyboard("main")
        
        await update.message.reply_html(text, reply_markup=keyboard)

    except Exception as e:
        logger.error(f"Erro no help_command para o usuário {user.id}: {e}", exc_info=True)
        # Mensagem de fallback caso ocorra um erro
        await update.message.reply_text("Olá! Sou seu Maestro Financeiro. Use os botões para explorar minhas funções.")
    finally:
        db.close()

async def help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Processa os cliques nos botões do menu de ajuda, editando a mensagem
    para mostrar a seção correspondente.
    """
    query = update.callback_query
    await query.answer() # Responde ao clique para o Telegram saber que foi processado

    try:
        # Extrai a seção do callback_data (ex: "help_analise" -> "analise")
        section = query.data.split('_')[1]

        if section in HELP_TEXTS:
            text = HELP_TEXTS[section]
            
            # Se a seção for a principal, personaliza com o nome do usuário novamente
            if section == "main":
                user = query.from_user
                db = next(get_db())
                try:
                    usuario_db = db.query(Usuario).filter(Usuario.telegram_id == user.id).first()
                    user_name = usuario_db.nome_completo.split(' ')[0] if usuario_db and usuario_db.nome_completo else user.first_name
                    text = text.format(user_name=user_name)
                finally:
                    db.close()

            keyboard = get_help_keyboard(section)
            
            # Verifica se o conteúdo realmente mudou antes de editar
            try:
                # Edita a mensagem original com o novo texto e teclado
                await query.edit_message_text(text, parse_mode='HTML', reply_markup=keyboard)
            except Exception as edit_error:
                # Se der erro de "Message is not modified", apenas ignora
                if "Message is not modified" in str(edit_error):
                    logger.debug("Mensagem de ajuda não foi modificada (conteúdo idêntico)")
                    await query.answer()
                else:
                    raise edit_error
            
    except (IndexError, KeyError) as e:
        logger.error(f"Erro no help_callback: Seção não encontrada. query.data: {query.data}. Erro: {e}")
        await query.answer("Erro: Seção de ajuda não encontrada.", show_alert=True)
    except Exception as e:
        logger.error(f"Erro inesperado no help_callback: {e}", exc_info=True)
        await query.answer("Ocorreu um erro ao carregar a ajuda. Tente novamente.", show_alert=True)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    db = next(get_db())
    try:
        user = get_or_create_user(db, update.effective_user.id, update.effective_user.full_name)
        if user and user.nome_completo:
            await help_command(update, context)
            return ConversationHandler.END
        else:
            await update.message.reply_text("Olá! Sou seu assistente financeiro. Para uma experiência mais personalizada, como posso te chamar?")
            return ASK_NAME
    finally:
        db.close()

async def receive_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_name = update.message.text.strip()
    user_info = update.effective_user
    db = next(get_db())
    try:
        usuario_db = get_or_create_user(db, user_info.id, user_name)
        usuario_db.nome_completo = user_name
        db.commit()
        await update.message.reply_text(f"Prazer em conhecer, {user_name.split(' ')[0]}! 😊")
        await help_command(update, context)
    finally:
        db.rollback()
        db.close()
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.message or (update.callback_query and update.callback_query.message)
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("Operação cancelada. ✅")
    else:
        await message.reply_text("Operação cancelada. ✅")
    context.user_data.clear()
    return ConversationHandler.END

# --- HANDLER DE GERENTE FINANCEIRO (IA) - VERSÃO MELHORADA ---

async def start_gerente(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    db = next(get_db())
    try:
        user = get_or_create_user(db, update.effective_user.id, update.effective_user.full_name)
        user_name = user.nome_completo.split(' ')[0] if user.nome_completo else "você"
        contexto = obter_contexto_usuario(context)
        
        if contexto.historico:
            mensagem = f"Oi de novo, {user_name}! 😊 No que posso te ajudar hoje?"
        else:
            # Saudação épica e profissional
            mensagem = f"""
🎩 <b>Olá, {user_name}!</b>

Sou seu <b>Maestro Financeiro</b> - um analista sênior especializado em transformar seus dados em decisões inteligentes. 

<b>💡 O que posso fazer por você:</b>
• Analisar padrões nos seus gastos
• Calcular seu score de saúde financeira
• Comparar períodos e detectar tendências
• Sugerir estratégias personalizadas
• Projetar cenários futuros

<b>🎯 Exemplos do que você pode perguntar:</b>
<i>"Qual meu score de saúde financeira?"</i>
<i>"Compare meus gastos de abril com março"</i>
<i>"Onde posso economizar este mês?"</i>
<i>"Como está minha maior meta?"</i>

Estou aqui para ser muito mais que um consultor - sou seu parceiro estratégico rumo à prosperidade! 

<b>Por onde começamos?</b> 🚀
"""
                        
        await update.message.reply_html(mensagem)
        return AWAIT_GERENTE_QUESTION
    finally:
        db.close()

async def handle_natural_language(update: Update, context: ContextTypes.DEFAULT_TYPE, custom_question: str = None) -> int:
    """
    Handler principal para o /gerente (V4).
    1. Despacha para cotações externas.
    2. Envia para a IA.
    3. Executa funções com base na resposta da IA (JSON) ou envia a análise de texto.
    """
    # --- Correção do Bug de Botão (AttributeError) ---
    is_callback = update.callback_query is not None
    if is_callback:
        effective_message = update.callback_query.message
        user_question = custom_question or ""
        effective_user = update.callback_query.from_user
    else:
        effective_message = update.message
        user_question = effective_message.text
        effective_user = update.effective_user

    chat_id = effective_message.chat_id
    await context.bot.send_chat_action(chat_id=chat_id, action='typing')

    # --- Despachante: Verifica primeiro se é uma cotação ---
    flag_dado_externo, topico_dado_externo = detectar_intencao_e_topico(user_question)
    if flag_dado_externo:
        logger.info(f"Intenção de dado externo detectada: {topico_dado_externo}")
        dados = await obter_dados_externos(flag_dado_externo)
        await enviar_texto_em_blocos(context.bot, chat_id, dados.get("texto_html", "Não encontrei a informação."))
        return AWAIT_GERENTE_QUESTION

    # --- Se não for cotação, continua com a IA financeira ---
    db = next(get_db())
    contexto_conversa = obter_contexto_usuario(context)
    
    try:
        usuario_db = get_or_create_user(db, chat_id, effective_user.full_name)
        
        contexto_financeiro_str = await preparar_contexto_financeiro_completo(db, usuario_db)
        historico_conversa_str = contexto_conversa.get_contexto_formatado()

        # --- NOVO: VERIFICAR CACHE DE RESPOSTA DA IA ---
        from .services import _gerar_chave_resposta_ia, _obter_resposta_ia_cache, _salvar_resposta_ia_cache, _gerar_hash_dados_financeiros
        
        hash_dados = _gerar_hash_dados_financeiros(contexto_financeiro_str)
        chave_cache_ia = _gerar_chave_resposta_ia(usuario_db.id, user_question, hash_dados)
        
        resposta_cache = _obter_resposta_ia_cache(chave_cache_ia)
        if resposta_cache:
            logger.info(f"Resposta da IA obtida do cache para usuário {usuario_db.id}")
            resposta_ia = resposta_cache
        else:
            # Gera nova resposta
            prompt_final = PROMPT_GERENTE_VDM.format(
                user_name=usuario_db.nome_completo.split(' ')[0] if usuario_db.nome_completo else "você",
                pergunta_usuario=user_question,
                contexto_financeiro_completo=contexto_financeiro_str,
                contexto_conversa=historico_conversa_str
            )
            
            model = genai.GenerativeModel(config.GEMINI_MODEL_NAME)
            response = await model.generate_content_async(prompt_final)
            resposta_ia = _limpar_resposta_ia(response.text)
            
            # Salva no cache
            _salvar_resposta_ia_cache(chave_cache_ia, resposta_ia)
        
        # --- Lógica de Decisão: É uma chamada de função (JSON) ou uma análise (texto)? ---
        try:
            # Tenta decodificar a resposta como JSON
            dados_funcao = json.loads(resposta_ia)
            if isinstance(dados_funcao, dict) and "funcao" in dados_funcao:
                nome_funcao = dados_funcao.get("funcao")
                parametros = dados_funcao.get("parametros", {})
                
                if nome_funcao == "listar_lancamentos":
                    await handle_lista_lancamentos(chat_id, context, parametros)
                else:
                    logger.warning(f"IA tentou chamar uma função desconhecida: {nome_funcao}")
                    await context.bot.send_message(chat_id, "A IA tentou uma ação que não conheço.")
            else:
                # Se não for um JSON de função, trata como texto normal.
                raise json.JSONDecodeError("Não é um JSON de função", resposta_ia, 0)

        except json.JSONDecodeError:
            # Se não for JSON, é uma análise de texto. Envia para o usuário.
            resposta_texto, reply_markup = parse_action_buttons(resposta_ia)
            await enviar_texto_em_blocos(context.bot, chat_id, resposta_texto, reply_markup=reply_markup)
            contexto_conversa.adicionar_interacao(user_question, resposta_texto, tipo="gerente_vdm_analise")

    except Exception as e:
        logger.error(f"Erro CRÍTICO em handle_natural_language (V4) para user {chat_id}: {e}", exc_info=True)
        await enviar_resposta_erro(context.bot, chat_id)
    finally:
        db.close()
    
    return AWAIT_GERENTE_QUESTION

async def handle_dados_externos(update, context, user_question, usuario_db, contexto):
    flag, topico = detectar_intencao_e_topico(user_question)
    
    if flag:
        dados = await obter_dados_externos(flag)
        keyboard = [[InlineKeyboardButton("📈 Como isso me afeta?", callback_data=f"analise_{flag}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        resposta_texto = dados.get("texto_html", "Não encontrei a informação.")
        await enviar_texto_em_blocos(context.bot, usuario_db.telegram_id, resposta_texto, reply_markup=reply_markup)
        contexto.adicionar_interacao(user_question, resposta_texto, "dados_externos")

def _parse_filtros_lancamento(texto: str, db: Session, user_id: int) -> dict:
    """
    Extrai filtros de tipo, categoria, conta/forma de pagamento e data de um texto.
    """
    filtros = {}
    texto_lower = texto.lower()
    
    # --- CORREÇÃO: Definimos a lista no escopo principal da função ---
    formas_pagamento_comuns = ['pix', 'crédito', 'debito', 'dinheiro']

    # --- Filtro de TIPO ---
    PALAVRAS_GASTOS = ['gastos', 'despesas', 'saídas', 'saidas', 'paguei']
    PALAVRAS_RECEITAS = ['receitas', 'entradas', 'ganhei', 'recebi']

    if any(palavra in texto_lower for palavra in PALAVRAS_GASTOS):
        filtros['tipo'] = 'Saída'
    elif any(palavra in texto_lower for palavra in PALAVRAS_RECEITAS):
        filtros['tipo'] = 'Entrada'
    
    # --- Filtro de DATA ---
    hoje = datetime.now()
    if "mês passado" in texto_lower:
        primeiro_dia_mes_passado = (hoje.replace(day=1) - timedelta(days=1)).replace(day=1)
        ultimo_dia_mes_passado = hoje.replace(day=1) - timedelta(days=1)
        filtros['data_inicio'] = primeiro_dia_mes_passado.replace(hour=0, minute=0, second=0)
        filtros['data_fim'] = ultimo_dia_mes_passado.replace(hour=23, minute=59, second=59)
    # ... (outros filtros de data)

    # --- LÓGICA UNIFICADA PARA CONTA E FORMA DE PAGAMENTO ---
    filtro_conta_encontrado = False
    contas_usuario = db.query(Conta).filter(Conta.id_usuario == user_id).all()
    
    for conta in contas_usuario:
        padrao_conta = r'\b' + re.escape(conta.nome.lower()) + r'\b'
        if re.search(padrao_conta, texto_lower):
            filtros['id_conta'] = conta.id
            filtro_conta_encontrado = True
            logging.info(f"Filtro de CONTA específica detectado: '{conta.nome}' (ID: {conta.id})")
            break 
    
    if not filtro_conta_encontrado:
        for fp in formas_pagamento_comuns: # Agora a variável já existe
            padrao_fp = r'\b' + re.escape(fp) + r'\b'
            if fp == 'crédito' and 'cartão' not in texto_lower:
                continue
            if re.search(padrao_fp, texto_lower):
                filtros['forma_pagamento'] = fp
                logging.info(f"Filtro de FORMA DE PAGAMENTO genérica detectado: '{fp}'")
                break

    # --- Filtro de CATEGORIA ---
    categorias_comuns = ['lazer', 'alimentação', 'transporte', 'moradia', 'saúde', 'receitas', 'compras']
    for cat in categorias_comuns:
        padrao_cat = r'\b' + re.escape(cat) + r'\b'
        if re.search(padrao_cat, texto_lower):
            filtros['categoria_nome'] = cat
            break
            
    # --- Filtro de busca por texto geral (QUERY) ---
    match = re.search(r'com\s+([a-zA-Z0-9çãáéíóúâêô\s]+)', texto_lower)
    if match:
        termo_busca = match.group(1).strip()
        # A variável 'formas_pagamento_comuns' agora está sempre acessível
        eh_fp_ou_conta = any(fp in termo_busca for fp in formas_pagamento_comuns) or \
                         any(conta.nome.lower() in termo_busca for conta in contas_usuario)
        
        if not eh_fp_ou_conta:
             filtros['query'] = termo_busca
             logging.info(f"Filtro de QUERY por texto detectado: '{termo_busca}'")

    return filtros

def _limpar_resposta_ia(texto: str) -> str:
    """Remove os blocos de código markdown e HTML malformado que a IA às vezes adiciona."""
    # Remove ```html, ```json, ```
    texto_limpo = re.sub(r'^```(html|json)?\n', '', texto, flags=re.MULTILINE)
    texto_limpo = re.sub(r'```$', '', texto_limpo, flags=re.MULTILINE)
    
    # Remove DOCTYPE e outras tags HTML problemáticas
    texto_limpo = re.sub(r'<!DOCTYPE[^>]*>', '', texto_limpo, flags=re.IGNORECASE)
    texto_limpo = re.sub(r'<html[^>]*>', '', texto_limpo, flags=re.IGNORECASE)
    texto_limpo = re.sub(r'</html>', '', texto_limpo, flags=re.IGNORECASE)
    texto_limpo = re.sub(r'<head[^>]*>.*?</head>', '', texto_limpo, flags=re.IGNORECASE | re.DOTALL)
    texto_limpo = re.sub(r'<body[^>]*>', '', texto_limpo, flags=re.IGNORECASE)
    texto_limpo = re.sub(r'</body>', '', texto_limpo, flags=re.IGNORECASE)
    
    # Remove tags <p> abertas sem fechamento
    texto_limpo = re.sub(r'<p\s*>', '\n', texto_limpo, flags=re.IGNORECASE)
    texto_limpo = re.sub(r'</p>', '\n', texto_limpo, flags=re.IGNORECASE)
    
    # CORREÇÃO: Converte asteriscos duplos em tags HTML <b>
    texto_limpo = re.sub(r'\*\*([^*]+?)\*\*', r'<b>\1</b>', texto_limpo)
    
    # Remove quebras de linha excessivas
    texto_limpo = re.sub(r'\n{3,}', '\n\n', texto_limpo)
    
    return texto_limpo.strip()

async def enviar_resposta_erro(bot, user_id):
    """Envia uma mensagem de erro amigável e aleatória para o usuário."""
    mensagens_erro = [
        "Ops! Meu cérebro deu uma pane. Tenta de novo? 🤖",
        "Eita! Algo deu errado aqui. Pode repetir a pergunta? 😅",
        "Hmm, parece que travei. Fala de novo aí! 🔄"
    ]
    try:
        await bot.send_message(chat_id=user_id, text=random.choice(mensagens_erro))
    except Exception as e:
        logger.error(f"Falha ao enviar mensagem de erro para o usuário {user_id}: {e}")

async def handle_lista_lancamentos(chat_id: int, context: ContextTypes.DEFAULT_TYPE, parametros: dict):
    """
    Busca e exibe uma lista de lançamentos com base nos parâmetros recebidos da IA.
    """
    logger.info(f"Executando handle_lista_lancamentos com parâmetros: {parametros}")
    db = next(get_db())
    try:
        # A função buscar_lancamentos_usuario já aceita esses parâmetros nomeados
        lancamentos = buscar_lancamentos_usuario(telegram_user_id=chat_id, **parametros)
        
        if not lancamentos:
            await context.bot.send_message(chat_id, "Não encontrei nenhum lançamento com os filtros que você pediu.")
            return

        limit = parametros.get('limit', len(lancamentos))
        resposta_final = f"Encontrei {len(lancamentos)} lançamento(s) com os critérios que você pediu:\n\n"
        
        cards_formatados = [formatar_lancamento_detalhado(lanc) for lanc in lancamentos]
        resposta_final += "\n\n".join(cards_formatados)

        await enviar_texto_em_blocos(context.bot, chat_id, resposta_final)
        
    finally:
        db.close()

async def handle_action_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Processa cliques em botões de ação gerados pela IA."""
    query = update.callback_query
    await query.answer()

    pergunta_simulada = query.data.replace("_", " ").capitalize()
    logger.info(f"Botão de ação clicado. Pergunta simulada para a IA: '{pergunta_simulada}'")
    
    if pergunta_simulada:
        await query.message.delete()
        # Chama a função principal de linguagem natural, passando a query e a pergunta simulada.
        await handle_natural_language(update, context, custom_question=pergunta_simulada)
            
    return AWAIT_GERENTE_QUESTION


async def handle_conversacional(update: Update, context: ContextTypes.DEFAULT_TYPE, user_question: str, usuario_db: Usuario, contexto: ContextoConversa):
    """
    Lida com saudações e interações casuais.
    """
    user_name = usuario_db.nome_completo.split(' ')[0] if usuario_db.nome_completo else "amigo"
    
    respostas = {
        "saudacao": [
            f"Olá, {user_name}! Como posso te ajudar a organizar suas finanças hoje?",
            f"E aí, {user_name}! Pronto pra deixar as contas em dia?",
            f"Opa, {user_name}! O que manda?"
        ],
        "agradecimento": [
            "De nada! Se precisar de mais alguma coisa, é só chamar.",
            "Disponha! Estou aqui pra isso.",
            "Tranquilo! Qualquer coisa, tô na área."
        ],
        "despedida": [
            "Até mais! Precisando, é só chamar.",
            "Falou! Se cuida.",
            "Tchau, tchau! Boas economias!"
        ]
    }
    
    pergunta_lower = user_question.lower()
    resposta_final = ""

    if any(s in pergunta_lower for s in ['oi', 'olá', 'bom dia', 'boa tarde', 'boa noite', 'tudo bem', 'blz', 'e aí']):
        resposta_final = random.choice(respostas['saudacao'])
    elif any(s in pergunta_lower for s in ['obrigado', 'vlw', 'valeu', 'obg']):
        resposta_final = random.choice(respostas['agradecimento'])
    elif any(s in pergunta_lower for s in ['tchau', 'até mais', 'falou']):
        resposta_final = random.choice(respostas['despedida'])
    else:
        # Fallback para caso a intenção seja conversacional, mas não mapeada
        resposta_final = f"Entendido, {user_name}! Se tiver alguma pergunta específica sobre suas finanças, pode mandar."
        
    await update.message.reply_text(resposta_final)
    contexto.adicionar_interacao(user_question, resposta_final, "conversacional")

async def handle_maior_despesa(update, context, user_question, usuario_db, contexto, db):
    """Encontra e exibe o maior gasto em um período."""
    filtros = _parse_filtros_lancamento(user_question)
    
    # Força o tipo para 'Saída' e limita a 1 resultado
    filtros['tipo'] = 'Saída'
    
    # A busca agora é por valor, não por data
    maior_gasto = db.query(Lancamento).filter(
        Lancamento.id_usuario == usuario_db.id,
        Lancamento.tipo == 'Saída'
    )
    if filtros.get('data_inicio'):
        maior_gasto = maior_gasto.filter(Lancamento.data_transacao >= filtros['data_inicio'])
    if filtros.get('data_fim'):
        maior_gasto = maior_gasto.filter(Lancamento.data_transacao <= filtros['data_fim'])

    maior_gasto = maior_gasto.order_by(Lancamento.valor.desc()).first()

    if not maior_gasto:
        await update.message.reply_text("Não encontrei nenhuma despesa para o período que você pediu.")
        return

    resposta_texto = (
        f"Sua maior despesa no período foi:\n\n"
        f"{formatar_lancamento_detalhado(maior_gasto)}"
    )
    await enviar_texto_em_blocos(context.bot, usuario_db.telegram_id, resposta_texto)
    contexto.adicionar_interacao(user_question, f"Mostrou maior despesa: {maior_gasto.descricao}", "maior_despesa")


async def handle_analise_geral(update, context, user_question, usuario_db, contexto, db):
    tipo_filtro = None
    if any(palavra in user_question.lower() for palavra in ['gastei', 'gasto', 'despesa']):
        tipo_filtro = 'Saída'
    elif any(palavra in user_question.lower() for palavra in ['ganhei', 'recebi', 'receita']):
        tipo_filtro = 'Entrada'

    # --- MUDANÇA: APLICAMOS O FILTRO DE CONTA AQUI TAMBÉM ---
    filtros_iniciais = _parse_filtros_lancamento(user_question, db, usuario_db.id)
    if tipo_filtro:
        filtros_iniciais['tipo'] = tipo_filtro

    # Buscamos todos os lançamentos que correspondem aos filtros iniciais
    lancamentos = buscar_lancamentos_usuario(
        telegram_user_id=usuario_db.telegram_id,
        limit=200, # Pegamos um limite alto para a análise
        **filtros_iniciais
    )
    
    if not lancamentos:
        await update.message.reply_text("Não encontrei nenhum lançamento para sua pergunta.")
        return
    
     # --- NOVA LÓGICA PARA DEFINIR O PERÍODO DA ANÁLISE ---
    data_mais_antiga = min(l.data_transacao for l in lancamentos)
    data_mais_recente = max(l.data_transacao for l in lancamentos)
    periodo_analise_str = f"de {data_mais_antiga.strftime('%d/%m/%Y')} a {data_mais_recente.strftime('%d/%m/%Y')}"
    # ---------------------------------------------------------

    # --- NOVO: PRÉ-CÁLCULO DO VALOR TOTAL ---
    valor_total_calculado = sum(float(l.valor) for l in lancamentos)

    contexto_json = preparar_contexto_json(lancamentos)
    analise_comportamental = analisar_comportamento_financeiro(lancamentos)
    analise_json = json.dumps(analise_comportamental, indent=2, ensure_ascii=False)
    
    # Passamos o valor pré-calculado para o prompt
    prompt_usado = PROMPT_GERENTE_VDM.format(
        user_name=usuario_db.nome_completo or "você",
        perfil_investidor=usuario_db.perfil_investidor or "Não definido",
        pergunta_usuario=user_question,
        contexto_json=contexto_json,
        analise_comportamental_json=analise_json,
        periodo_analise=periodo_analise_str,
        valor_total_pre_calculado=valor_total_calculado 
    )
    
    await gerar_resposta_ia(update, context, prompt_usado, user_question, usuario_db, contexto, "analise_geral")


async def gerar_resposta_ia(update, context, prompt, user_question, usuario_db, contexto, tipo_interacao):
    try:
        model = genai.GenerativeModel(config.GEMINI_MODEL_NAME)
        response = await model.generate_content_async(prompt)
        
        # --- NOVA LÓGICA DE PROCESSAMENTO JSON (MAIS SEGURA) ---
        
        # 1. Tenta encontrar o bloco JSON na resposta da IA
        json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
        
        # 2. Se NÃO encontrar um JSON, trata o erro elegantemente
        if not json_match:
            logger.error(f"A IA não retornou um JSON válido. Resposta recebida: {response.text}")
            # Usa a resposta em texto livre da IA como um fallback, se fizer sentido
            # ou envia uma mensagem de erro padrão.
            await update.message.reply_text(
                "Hmm, não consegui estruturar a resposta. Aqui está o que a IA disse:\n\n"
                f"<i>{response.text}</i>",
                parse_mode='HTML'
            )
            # Adiciona ao contexto para não perder o histórico
            contexto.adicionar_interacao(user_question, response.text, tipo_interacao)
            return # Sai da função

        # 3. Se encontrou um JSON, tenta decodificá-lo
        try:
            dados_ia = json.loads(json_match.group(0))
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao decodificar JSON da IA: {e}\nString Tentada: {json_match.group(0)}")
            await enviar_resposta_erro(context.bot, usuario_db.telegram_id)
            return

        # 4. Se o JSON foi decodificado, monta a mensagem formatada
        # (O código de formatação que fizemos antes continua aqui, sem alterações)
        titulo = dados_ia.get("titulo_resposta", "Análise Rápida")
        valor_total = dados_ia.get("valor_total", 0.0)
        comentario = dados_ia.get("comentario_maestro", "Aqui está o que encontrei.")
        detalhamento = dados_ia.get("detalhamento", [])
        proximo_passo = dados_ia.get("proximo_passo", {})

        mensagem_formatada = f"<b>{titulo}</b>\n"
        mensagem_formatada += f"━━━━━━━━━━━━━━━━━━\n\n"
        
        # Adiciona o valor total apenas se for maior que zero
        if valor_total > 0:
            mensagem_formatada += f"O valor total foi de <code>R$ {valor_total:.2f}</code>.\n\n"
        
        if detalhamento:
            mensagem_formatada += "Aqui está o detalhamento:\n"
            for item in detalhamento:
                emoji = item.get("emoji", "🔹")
                nome_item = item.get("item", "N/A")
                valor_item = item.get("valor", 0.0)
                mensagem_formatada += f"{emoji} <b>{nome_item}:</b> <code>R$ {valor_item:.2f}</code>\n"
            mensagem_formatada += "\n"

        mensagem_formatada += f"<i>{comentario}</i>\n"

        keyboard = None
        if proximo_passo and proximo_passo.get("botao_texto"):
            mensagem_formatada += f"\n💡 <b>Próximo Passo:</b> {proximo_passo.get('texto', '')}"
            keyboard = [[
                InlineKeyboardButton(
                    proximo_passo["botao_texto"], 
                    callback_data=proximo_passo["botao_callback"]
                )
            ]]
        
        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None

        await enviar_texto_em_blocos(
            context.bot, 
            usuario_db.telegram_id, 
            mensagem_formatada, 
            reply_markup=reply_markup
        )
        contexto.adicionar_interacao(user_question, mensagem_formatada, tipo_interacao)
        
    except Exception as e:
        logger.error(f"Erro geral e inesperado em gerar_resposta_ia: {e}", exc_info=True)
        await enviar_resposta_erro(context.bot, usuario_db.telegram_id)

# --- HANDLER PARA CALLBACK DE ANÁLISE DE IMPACTO ---

async def handle_analise_impacto_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Processa o clique no botão "Como isso me afeta?", busca dados financeiros
    do usuário, gera e envia uma análise de impacto personalizada usando a IA.
    """
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    if not callback_data.startswith("analise_"):
        return
    
    tipo_dado = callback_data.replace("analise_", "")
    
    db = next(get_db())
    try:
        user_info = query.from_user
        usuario_db = get_or_create_user(db, user_info.id, user_info.full_name)
        
        # Edita a mensagem para dar feedback ao usuário
        await query.edit_message_text("Analisando o impacto para você... 🧠")
        
        # Busca os dados externos (cotação, etc.)
        dados_externos = await obter_dados_externos(tipo_dado)
        informacao_externa = dados_externos.get("texto_html", "Informação não disponível")
        
        # Busca o contexto financeiro do usuário
        lancamentos = buscar_lancamentos_com_relacionamentos(db, usuario_db.telegram_id)
        contexto_json = services.preparar_contexto_json(lancamentos)
        
        # Monta o prompt para a IA
        prompt_impacto = PROMPT_ANALISE_IMPACTO.format(
            user_name=usuario_db.nome_completo or "você",
            perfil_investidor=usuario_db.perfil_investidor or "Não definido",
            informacao_externa=informacao_externa,
            contexto_json=contexto_json
        )
        
        # Chama a IA para gerar a análise
        model = genai.GenerativeModel(config.GEMINI_MODEL_NAME)
        response = await model.generate_content_async(prompt_impacto)
        resposta_bruta = response.text
        resposta_limpa = _limpar_resposta_ia(resposta_bruta)
        
        
        # 2. Envia a resposta limpa para o usuário.
        await query.edit_message_text(
            text=resposta_limpa,  # <--- Usa a variável corrigida
            parse_mode='HTML',
            disable_web_page_preview=True
        )
        
    except Exception as e:
        logger.error(f"Erro na análise de impacto: {e}", exc_info=True)
        # Envia uma mensagem de erro amigável se algo der errado
        await query.edit_message_text(
            text="😅 Ops! Não consegui gerar a análise de impacto. Tente novamente mais tarde.",
            parse_mode='HTML'
        )
    finally:
        db.close()


# === HANDLERS DE MACHINE LEARNING ===

async def ml_analise_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Comando /ml - Análise completa com Machine Learning
    """
    try:
        user_id = update.effective_user.id
        
        # Mensagem inicial
        await update.message.reply_text(
            "🧠 <b>Análise ML Iniciada</b>\n\n"
            "Analisando seus dados financeiros com algoritmos avançados...",
            parse_mode='HTML'
        )
        
        db = next(get_db())
        try:
            resultado = services.analisar_financas_com_ml(db, user_id)
            
            if "erro" in resultado:
                await update.message.reply_text(
                    f"❌ <b>Erro:</b> {resultado['erro']}",
                    parse_mode='HTML'
                )
                return
            
            # Formatar resultado
            resposta = "🧠 <b>ANÁLISE MACHINE LEARNING</b>\n\n"
            
            # Score de Saúde
            score_info = resultado.get("score_saude", {})
            if score_info:
                emoji = score_info.get("emoji", "📊")
                nivel = score_info.get("nivel", "")
                score = score_info.get("score", 0)
                
                resposta += f"{emoji} <b>Saúde Financeira:</b> {nivel}\n"
                resposta += f"📈 <b>Score:</b> {score}/100\n\n"
                
                # Detalhes do score
                detalhes = score_info.get("detalhes", {})
                if detalhes:
                    resposta += "<b>Componentes do Score:</b>\n"
                    resposta += f"💰 Poupança: {detalhes.get('taxa_poupanca', 0):.1f}%\n"
                    resposta += f"📊 Consistência: {detalhes.get('consistencia', 0):.1f}%\n"
                    resposta += f"🎯 Diversificação: {detalhes.get('diversificacao', 0):.1f}%\n"
                    resposta += f"🔍 Controle: {detalhes.get('controle_gastos', 0):.1f}%\n\n"
            
            # Anomalias
            anomalias = resultado.get("anomalias", {})
            if anomalias.get("total_anomalias", 0) > 0:
                total = anomalias["total_anomalias"]
                percentual = anomalias.get("percentual_anomalias", 0)
                resposta += f"⚠️ <b>Anomalias Detectadas:</b> {total} ({percentual:.1f}%)\n\n"
            
            # Previsões
            previsoes = resultado.get("previsoes", {})
            if "previsoes" in previsoes and previsoes["previsoes"]:
                resposta += "<b>🔮 Previsões:</b>\n"
                for prev in previsoes["previsoes"][:2]:  # Máximo 2
                    mes = prev["mes"]
                    valor = prev["previsao_gasto"]
                    confianca = prev["confianca"]
                    resposta += f"📅 {mes}: R$ {valor:.2f} (Conf: {confianca})\n"
                resposta += "\n"
            
            # Clusters
            clustering = resultado.get("clustering", {})
            if "clusters" in clustering:
                clusters = clustering["clusters"]
                if clusters:
                    resposta += f"🎯 <b>Padrões Identificados:</b> {len(clusters)} grupos\n"
                    # Mostrar principal cluster
                    cluster_principal = max(clusters, key=lambda x: x.get("tamanho", 0))
                    resposta += f"📌 Principal: {cluster_principal.get('descricao_comportamento', 'N/A')}\n\n"
            
            # Informações técnicas
            resposta += f"📊 <b>Dados:</b> {resultado.get('total_transacoes', 0)} transações em {resultado.get('periodo_analise', 90)} dias"
            
            await update.message.reply_text(resposta, parse_mode='HTML')
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Erro no comando ML: {str(e)}")
        await update.message.reply_text(
            "❌ Erro na análise ML. Tente novamente mais tarde.",
            parse_mode='HTML'
        )

async def previsao_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Comando /previsao - Previsão de gastos futuros
    """
    try:
        user_id = update.effective_user.id
        
        # Parâmetros
        meses = 3
        if context.args and context.args[0].isdigit():
            meses = min(int(context.args[0]), 6)  # Máximo 6 meses
        
        db = next(get_db())
        try:
            resultado = services.prever_gastos_futuros(db, user_id, meses)
            
            if "erro" in resultado:
                await update.message.reply_text(
                    f"❌ <b>Erro:</b> {resultado['erro']}",
                    parse_mode='HTML'
                )
                return
            
            resposta = "🔮 <b>PREVISÃO DE GASTOS</b>\n\n"
            
            # Tendência geral
            tendencia = resultado.get("tendencia", "estável")
            if tendencia == "crescente":
                emoji_tend = "📈"
            elif tendencia == "decrescente":
                emoji_tend = "📉"
            else:
                emoji_tend = "➡️"
            
            resposta += f"{emoji_tend} <b>Tendência:</b> {tendencia.title()}\n\n"
            
            # Previsões detalhadas
            previsoes = resultado.get("previsoes", [])
            if previsoes:
                resposta += "<b>📅 Previsões Mensais:</b>\n"
                for prev in previsoes:
                    mes = prev["mes"]
                    valor = prev["previsao_gasto"]
                    confianca = prev["confianca"]
                    
                    # Emoji para confiança
                    if confianca == "Alta":
                        emoji_conf = "🟢"
                    elif confianca == "Média":
                        emoji_conf = "🟡"
                    else:
                        emoji_conf = "🔴"
                    
                    resposta += f"{emoji_conf} <b>{mes}:</b> R$ {valor:.2f} ({confianca})\n"
            
            # Informações adicionais
            variacao = resultado.get("variacao_media_mensal", 0)
            if variacao != 0:
                resposta += f"\n📊 <b>Variação Média:</b> R$ {variacao:.2f}/mês\n"
            
            r2_score = resultado.get("r2_score", 0)
            resposta += f"🎯 <b>Precisão do Modelo:</b> {r2_score*100:.1f}%\n"
            resposta += f"📈 <b>Dados Históricos:</b> {resultado.get('dados_historicos', 0)} meses"
            
            await update.message.reply_text(resposta, parse_mode='HTML')
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Erro no comando previsão: {str(e)}")
        await update.message.reply_text(
            "❌ Erro na previsão. Tente novamente mais tarde.",
            parse_mode='HTML'
        )

async def anomalias_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Comando /anomalias - Detecta gastos anômalos
    """
    try:
        user_id = update.effective_user.id
        
        db = next(get_db())
        try:
            resultado = services.detectar_anomalias_financeiras(db, user_id)
            
            if "erro" in resultado:
                await update.message.reply_text(
                    f"❌ <b>Erro:</b> {resultado['erro']}",
                    parse_mode='HTML'
                )
                return
            
            anomalias = resultado.get("anomalias", [])
            total_anomalias = resultado.get("total_anomalias", 0)
            percentual = resultado.get("percentual_anomalias", 0)
            
            resposta = "⚠️ <b>ANOMALIAS DETECTADAS</b>\n\n"
            resposta += f"Total de anomalias encontradas: {total_anomalias} ({percentual:.1f}%)\n\n"
            
            for anomalia in anomalias:
                descricao = anomalia.get("descricao", "Descrição não disponível")
                valor = anomalia.get("valor", 0.0)
                data = anomalia.get("data", "Data não disponível")
                
                resposta += f"🔍 <b>Descrição:</b> {descricao}\n"
                resposta += f"💰 <b>Valor:</b> R$ {valor:.2f}\n"
                resposta += f"📅 <b>Data:</b> {data}\n\n"
            
            await update.message.reply_text(resposta, parse_mode='HTML')
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Erro no comando anomalias: {str(e)}")
        await update.message.reply_text(
            "❌ Erro na detecção de anomalias. Tente novamente mais tarde.",
            parse_mode='HTML'
        )

async def treinar_modelo_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Comando /treinar - Treina um modelo personalizado para o usuário
    """
    try:
        user_id = update.effective_user.id
        
        await update.message.reply_text(
            "🤖 <b>Treinamento Iniciado</b>\n\n"
            "Analisando seus dados para criar um modelo personalizado...",
            parse_mode='HTML'
        )
        
        db = next(get_db())
        try:
            resultado = services.treinar_modelo_categorias(db, user_id)
            
            if "erro" in resultado:
                await update.message.reply_text(
                    f"❌ <b>Erro:</b> {resultado['erro']}\n\n"
                    "💡 <b>Dica:</b> Categorize mais transações para melhorar o treinamento!",
                    parse_mode='HTML'
                )
                return
            
            accuracy = resultado.get("accuracy", 0)
            categorias = resultado.get("categorias_unicas", 0)
            amostras = resultado.get("total_amostras", 0)
            features = resultado.get("features_importantes", [])
            
            resposta = "🤖 <b>MODELO TREINADO</b>\n\n"
            resposta += f"🎯 <b>Precisão:</b> {accuracy*100:.1f}%\n"
            resposta += f"📊 <b>Categorias:</b> {categorias}\n"
            resposta += f"💾 <b>Amostras:</b> {amostras}\n\n"
            
            if features:
                resposta += "<b>🔍 Features Importantes:</b>\n"
                for feature, importancia in features[:3]:  # Top 3
                    resposta += f"• {feature}: {importancia*100:.1f}%\n"
            
            resposta += "\n✅ <b>Modelo personalizado criado!</b>\n"
            resposta += "Agora as próximas transações serão classificadas automaticamente."
            
            await update.message.reply_text(resposta, parse_mode='HTML')
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Erro no treinamento: {str(e)}")
        await update.message.reply_text(
            "❌ Erro no treinamento do modelo. Tente novamente mais tarde.",
            parse_mode='HTML'
        )

async def clusters_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Comando /clusters - Análise de padrões de comportamento
    """
    try:
        user_id = update.effective_user.id
        
        db = next(get_db())
        try:
            resultado = services.analisar_comportamento_clusters(db, user_id)
            
            if "erro" in resultado:
                await update.message.reply_text(
                    f"❌ <b>Erro:</b> {resultado['erro']}",
                    parse_mode='HTML'
                )
                return
            
            clusters = resultado.get("clusters", [])
            numero_clusters = resultado.get("numero_clusters", 0)
            
            resposta = "🎯 <b>ANÁLISE DE COMPORTAMENTO</b>\n\n"
            resposta += f"📊 <b>Padrões Identificados:</b> {numero_clusters}\n\n"
            
            # Ordenar clusters por tamanho
            clusters_ordenados = sorted(clusters, key=lambda x: x.get("tamanho", 0), reverse=True)
            
            for i, cluster in enumerate(clusters_ordenados):
                cluster_id = cluster.get("cluster_id", i)
                tamanho = cluster.get("tamanho", 0)
                valor_medio = cluster.get("valor_medio", 0)
                descricao = cluster.get("descricao_comportamento", "")
                categorias = cluster.get("categorias_principais", {})
                
                resposta += f"🔸 <b>Padrão {cluster_id + 1}</b> ({tamanho} transações)\n"
                resposta += f"💰 Valor médio: R$ {valor_medio:.2f}\n"
                resposta += f"📝 {descricao}\n"
                
                # Principal categoria
                if categorias:
                    principal_cat = list(categorias.keys())[0]
                    resposta += f"🏷️ Principal: {principal_cat}\n"
                
                resposta += "\n"
            
            resposta += "💡 <b>Use esses insights para otimizar seus gastos!</b>"
            
            await update.message.reply_text(resposta, parse_mode='HTML')
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Erro no comando clusters: {str(e)}")
        await update.message.reply_text(
            "❌ Erro na análise de clusters. Tente novamente mais tarde.",
            parse_mode='HTML'
        )

# === FUNÇÃO PARA ADICIONAR HANDLERS DE ML AO BOT ===

def add_ml_handlers(application):
    """
    Adiciona todos os handlers de Machine Learning ao bot
    """
    application.add_handler(CommandHandler("ml", ml_analise_command))
    application.add_handler(CommandHandler("previsao", previsao_command))
    application.add_handler(CommandHandler("anomalias", anomalias_command))
    application.add_handler(CommandHandler("treinar", treinar_modelo_command))
    application.add_handler(CommandHandler("clusters", clusters_command))
    
    logger.info("Handlers de Machine Learning adicionados ao bot")

# === CONVERSATION HANDLERS ===

def create_gerente_conversation_handler():
    """
    Cria o conversation handler para o /gerente (chat com IA)
    """
    return ConversationHandler(
        entry_points=[CommandHandler("gerente", start_gerente)],
        states={
            AWAIT_GERENTE_QUESTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_natural_language),
                CallbackQueryHandler(handle_action_button_callback, pattern="^(.*(?<!help).*)$")
            ]
        },
        fallbacks=[CommandHandler("cancelar", cancel)],
        per_chat=True,
        allow_reentry=True
    )

def create_onboarding_conversation_handler():
    return ConversationHandler(
        entry_points=[CommandHandler("start", start_command)],
        states={
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_name)],
        },
        fallbacks=[CommandHandler("cancelar", cancel)],
        per_chat=True
    )