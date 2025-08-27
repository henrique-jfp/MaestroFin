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
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler, CallbackQueryHandler
)

# Importando a função que vamos criar no próximo passo
from database.database import deletar_todos_dados_usuario
from .services import *
from .messages import render_message # Reutilizamos a função de cancelamento
from .states import CONFIRM_DELETION

logger = logging.getLogger(__name__)

async def start_delete_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia o fluxo de exclusão de dados do usuário."""
    
    # Mensagem de aviso enfática, como você pediu
    text = (
        "🚨 <b>ATENÇÃO: AÇÃO IRREVERSÍVEL</b> 🚨\n\n"
        "Você tem <b>CERTEZA ABSOLUTA</b> que deseja apagar "
        "<u>todos os seus dados financeiros</u> do Maestro?\n\n"
        "Isso inclui:\n"
        "  - Todos os lançamentos\n"
        "  - Todas as metas\n"
        "  - Todos os agendamentos\n"
        "  - Todas as configurações de contas e perfil\n\n"
        "Uma vez confirmada, a exclusão é <b>PERMANENTE</b> e não poderá ser desfeita."
    )
    
    keyboard = [
        [
            InlineKeyboardButton("🗑️ SIM, APAGAR TUDO", callback_data="delete_confirm_yes"),
            InlineKeyboardButton("👍 NÃO, CONTINUAR USANDO", callback_data="delete_confirm_no")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_html(text, reply_markup=reply_markup)
    
    return CONFIRM_DELETION

async def handle_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Processa a confirmação do usuário."""
    query = update.callback_query
    await query.answer()
    
    action = query.data
    
    if action == "delete_confirm_yes":
        user_id = query.from_user.id
        await query.edit_message_text(render_message("processando_solicitacao"))
        
        # Chama a função do banco de dados para fazer a exclusão
        sucesso = deletar_todos_dados_usuario(telegram_id=user_id)
        
        if sucesso:
            await query.edit_message_text(
                "✅ Seus dados foram permanentemente apagados.\n\n"
                "Obrigado por usar o Maestro Financeiro. Se mudar de ideia, "
                "basta usar o comando /start para começar de novo."
            )
            logger.info(f"Usuário {user_id} apagou todos os seus dados.")
        else:
            await query.edit_message_text(
                "❌ Ocorreu um erro ao tentar apagar seus dados. "
                "Nossa equipe foi notificada."
            )
            
        return ConversationHandler.END
        
    else: # delete_confirm_no
        await query.edit_message_text(render_message("operacao_cancelada"))
        return ConversationHandler.END

# Cria o ConversationHandler para ser importado no bot.py
delete_user_conv = ConversationHandler(
    entry_points=[CommandHandler('apagartudo', start_delete_flow)],
    states={
        CONFIRM_DELETION: [CallbackQueryHandler(handle_confirmation, pattern='^delete_confirm_')]
    },
    fallbacks=[CommandHandler('cancelar', cancel)],
    per_message=False,  # False porque mistura CommandHandler e CallbackQueryHandler
    per_user=True,
    per_chat=True
)