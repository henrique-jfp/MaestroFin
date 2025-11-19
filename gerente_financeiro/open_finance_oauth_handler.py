"""
gerente_financeiro/open_finance_oauth_handler.py

Handler de Conversa para o fluxo de Open Finance no Telegram.
Responsabilidade Única: Gerenciar a interação com o usuário (mensagens, botões),
chamar o OpenFinanceService para executar a lógica de negócio e apresentar os
resultados de forma clara e amigável.
"""
import asyncio
import logging
from typing import Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

from database.database import get_db
from open_finance.service import OpenFinanceService
from open_finance.pluggy_client import PluggyClient, PluggyClientError
from config import PLUGGY_WHITELIST_IDS

logger = logging.getLogger(__name__)

# Estados da conversa
SELECTING_BANK, AWAITING_CPF, WAITING_AUTH = range(3)


# --- Funções Auxiliares de UI ---

def _build_banks_keyboard(connectors: list) -> InlineKeyboardMarkup:
    """Constrói o teclado de seleção de bancos de forma curada e ordenada."""
    
    # Lista de bancos prioritários com seus nomes-chave e emojis
    PRIORITY_BANKS = {
        "Itaú": ("Itaú", "🟧"),
        "Bradesco": ("Bradesco", "🔴"),
        "Inter": ("Inter", "🟠"),
        "Nubank": ("Nubank", "🟣"),
        "Santander": ("Santander", "🔺"),
        "Caixa": ("Caixa", "🟦"),
        "Banco do Brasil": ("Banco do Brasil", "🟨"),
        "XP": ("XP", "⬛"),
    }
    
    # Filtra e monta a lista de bancos prioritários encontrados
    filtered_banks = []
    for bank_key, (display_name, emoji) in PRIORITY_BANKS.items():
        for conn in connectors:
            if bank_key.lower() in conn['name'].lower():
                filtered_banks.append({
                    "name": f"{emoji} {display_name}",
                    "id": conn['id']
                })
                break # Evita adicionar o mesmo banco duas vezes (ex: "Itaú" e "Itaucard")

    keyboard = []
    for bank in filtered_banks:
        keyboard.append([InlineKeyboardButton(bank['name'], callback_data=f"of_bank_{bank['id']}")])
    
    keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="of_cancel")])
    return InlineKeyboardMarkup(keyboard)

def _find_oauth_url(item_data: dict) -> Optional[str]:
    """Inspeciona a resposta da API da Pluggy para encontrar a URL de autorização."""
    if not item_data:
        return None
    
    # Tentativa 1: Chave 'url' no nível raiz (mais comum)
    if 'url' in item_data and isinstance(item_data['url'], str):
        return item_data['url']
        
    # Tentativa 2: Chave 'redirectUrl' no nível raiz
    if 'redirectUrl' in item_data and isinstance(item_data['redirectUrl'], str):
        return item_data['redirectUrl']

    # Tentativa 3: Dentro do objeto 'parameter'
    parameter = item_data.get('parameter')
    if isinstance(parameter, dict):
        if 'url' in parameter and isinstance(parameter['url'], str):
            return parameter['url']
        if 'data' in parameter and isinstance(parameter['data'], str) and parameter['data'].startswith('http'):
             return parameter['data']

    return None

# --- Handlers do ConversationHandler ---

async def start_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia o fluxo de conexão com /conectar_banco."""
    user_id = update.effective_user.id
    if PLUGGY_WHITELIST_IDS and user_id not in PLUGGY_WHITELIST_IDS:
        await update.message.reply_text("🔒 Esta funcionalidade está em beta fechado.")
        return ConversationHandler.END

    await update.message.reply_text("Buscando bancos disponíveis com Open Finance...")
    
    try:
        client = PluggyClient()
        connectors = client.get_connectors()
        oauth_connectors = [c for c in connectors if c.get("oauth")]
        oauth_connectors.sort(key=lambda x: x['name'])
        
        context.user_data['of_connectors'] = {c['id']: c for c in oauth_connectors}
        
        keyboard = _build_banks_keyboard(oauth_connectors)
        await update.message.reply_text("Selecione seu banco:", reply_markup=keyboard)
        return SELECTING_BANK
    except PluggyClientError as e:
        await update.message.reply_text(f"❌ Erro ao buscar bancos: {e}")
        return ConversationHandler.END

async def bank_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Processa a seleção do banco e pede o CPF."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if data == "of_cancel":
        await query.edit_message_text("Operação cancelada.")
        return ConversationHandler.END

    connector_id = int(data.split("_")[-1])
    connector = context.user_data.get("of_connectors", {}).get(connector_id)
    
    if not connector:
        await query.edit_message_text("Banco inválido. Tente novamente.")
        return ConversationHandler.END

    context.user_data["of_selected_connector"] = connector
    await query.edit_message_text(f"🏦 {connector['name']}\n\nPara iniciar a conexão, por favor, digite seu CPF (apenas números).")
    return AWAITING_CPF

async def handle_cpf(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Processa o CPF, cria o item na Pluggy e envia o link de autorização."""
    cpf = update.message.text.strip().replace(".", "").replace("-", "")
    if not (cpf.isdigit() and len(cpf) == 11):
        await update.message.reply_text("CPF inválido. Por favor, digite os 11 números.")
        return AWAITING_CPF

    try:
        await update.message.delete()
    except Exception:
        pass
        
    status_msg = await update.message.reply_text("⏳ Criando conexão segura...")

    user_id = update.effective_user.id
    connector = context.user_data["of_selected_connector"]
    
    db = next(get_db())
    service = OpenFinanceService(db)
    try:
        item = service.create_connection_item(user_id, connector['id'], cpf)
        item_id = item.get('id')

        if not item_id:
            raise PluggyClientError("A API não retornou um ID para a conexão criada.")

        # Usa a nova função auxiliar para encontrar a URL
        oauth_url = _find_oauth_url(item)

        if not oauth_url:
            # Fallback: aguarda um pouco e tenta novamente
            await asyncio.sleep(4)
            item_status = service.get_item_status(item_id)
            oauth_url = _find_oauth_url(item_status)
            if not oauth_url:
                 raise PluggyClientError("Não foi possível obter o link de autorização do banco após a criação.")

        keyboard = [
            [InlineKeyboardButton("🔐 Autorizar no Banco", url=oauth_url)],
            [InlineKeyboardButton("✅ Já autorizei", callback_data=f"of_authorized_{item_id}")]
        ]
        await status_msg.edit_text(
            f"Clique no botão para autorizar o acesso no site oficial do {connector['name']}. "
            "Depois, volte aqui e clique em 'Já autorizei'.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return WAITING_AUTH
        
    except PluggyClientError as e:
        logger.error(f"Erro de cliente Pluggy ao criar conexão: {e}")
        await status_msg.edit_text(f"❌ Erro ao iniciar a conexão com o banco: {e}")
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Erro inesperado em handle_cpf: {e}", exc_info=True)
        await status_msg.edit_text("❌ Ocorreu um erro inesperado. Tente novamente mais tarde.")
        return ConversationHandler.END
    finally:
        db.close()

async def authorized_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Verifica o status da conexão após o usuário autorizar."""
    query = update.callback_query
    await query.answer("Verificando...")
    
    item_id = query.data.split("_")[-1]
    
    await query.edit_message_text("🔄 Sincronizando dados da sua conta. Isso pode levar um minuto...")

    db = next(get_db())
    service = OpenFinanceService(db)
    try:
        # Loop de verificação
        for _ in range(10): # Tenta por até 50 segundos
            item_status = service.get_item_status(item_id)
            if item_status.get("status") in ("UPDATED", "PARTIAL_SUCCESS"):
                saved_item = service.save_connection_details(query.from_user.id, item_status)
                new_acc, _ = service.sync_accounts_for_item(saved_item)
                await query.edit_message_text(f"✅ Conexão bem-sucedida! {new_acc} conta(s) encontrada(s). Use /minhas_contas para ver os detalhes.")
                return ConversationHandler.END
            await asyncio.sleep(5)
            
        await query.edit_message_text("A conexão está demorando mais que o esperado. Vou continuar tentando em background e te aviso quando terminar.")
        return ConversationHandler.END
    except (PluggyClientError, ValueError) as e:
        await query.edit_message_text(f"❌ Erro na finalização da conexão: {e}")
        return ConversationHandler.END
    finally:
        db.close()


async def cancel_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela o fluxo de conversa."""
    message = update.message or update.callback_query.message
    await message.reply_text("Operação cancelada.")
    return ConversationHandler.END

# --- Handlers de Comandos Individuais ---

async def list_accounts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler para /minhas_contas."""
    user_id = update.effective_user.id
    db = next(get_db())
    service = OpenFinanceService(db)
    try:
        connections = service.get_user_connections(user_id)
        if not connections:
            await update.message.reply_html("Você não tem bancos conectados. Use <code>/conectar_banco</code>.")
            return

        response_text = "🏦 *Suas Conexões:*\n\n"
        for conn in connections:
            response_text += f"*{conn.connector_name}* (Status: `{conn.status}`)\n"
            for acc in conn.accounts:
                balance_str = f"R$ {acc.balance:,.2f}" if acc.balance is not None else "N/A"
                response_text += f"  - `{acc.name}`: {balance_str}\n"
            response_text += "\n"
        
        await update.message.reply_markdown(response_text)
    finally:
        db.close()


async def sync_transactions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler para /sincronizar."""
    await update.message.reply_text("🔄 Iniciando sincronização em background...")
    user_id = update.effective_user.id
    
    # Executa em background para não travar o bot
    context.application.create_task(
        _sync_transactions_background(user_id, context)
    )

async def _sync_transactions_background(user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Função de background para sincronizar transações."""
    db = next(get_db())
    service = OpenFinanceService(db)
    try:
        stats = service.sync_transactions_for_user(user_id)
        await context.bot.send_message(
            user_id,
            f"✅ Sincronização concluída! {stats['new_transactions']} nova(s) transação(ões) encontrada(s)."
        )
    except Exception as e:
        logger.error(f"Erro na sincronização em background: {e}")
        await context.bot.send_message(user_id, "❌ Erro durante a sincronização.")
    finally:
        db.close()


def get_open_finance_handlers():
    """Cria e retorna todos os handlers relacionados ao Open Finance."""
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("conectar_banco", start_flow)],
        states={
            SELECTING_BANK: [CallbackQueryHandler(bank_selected, pattern="^of_bank_")],
            AWAITING_CPF: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_cpf)],
            WAITING_AUTH: [CallbackQueryHandler(authorized_flow, pattern="^of_authorized_")]
        },
        fallbacks=[
            CommandHandler("cancelar", cancel_flow),
            CallbackQueryHandler(cancel_flow, pattern="^of_cancel$")
        ],
        per_user=True,
    )

    return [
        conv_handler,
        CommandHandler("minhas_contas", list_accounts),
        CommandHandler("sincronizar", sync_transactions),
        # O handler para /categorizar será adicionado aqui depois
    ]
