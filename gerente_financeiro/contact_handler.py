# gerente_financeiro/contact_handler.py

import logging
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters

logger = logging.getLogger(__name__)

# Estados para o conversation handler
CONTACT_NAME, CONTACT_MESSAGE = range(2)

async def contact_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia o fluxo de contato."""
    await update.message.reply_text(
        "📞 <b>Contato com Suporte</b>\n\n"
        "Olá! Como posso te ajudar?\n\n"
        "Por favor, me diga seu nome:",
        parse_mode='HTML'
    )
    return CONTACT_NAME

async def contact_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Processa o nome e pede a mensagem."""
    name = update.message.text.strip()
    context.user_data['contact_name'] = name

    await update.message.reply_text(
        f"👤 <b>{name}</b>\n\n"
        "Agora, por favor, descreva sua dúvida ou problema:",
        parse_mode='HTML'
    )
    return CONTACT_MESSAGE

async def contact_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Processa a mensagem e finaliza."""
    message = update.message.text.strip()
    name = context.user_data.get('contact_name', 'Usuário')

    # Aqui você pode implementar o envio do contato para suporte
    # Por exemplo, enviar email ou salvar no banco

    await update.message.reply_text(
        f"✅ <b>Mensagem enviada!</b>\n\n"
        f"📝 <b>De:</b> {name}\n"
        f"💬 <b>Mensagem:</b> {message}\n\n"
        f"Obrigado pelo contato! Nossa equipe irá responder em breve.",
        parse_mode='HTML'
    )

    context.user_data.clear()
    return ConversationHandler.END

async def contact_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela o contato."""
    await update.message.reply_text("❌ Contato cancelado.")
    context.user_data.clear()
    return ConversationHandler.END

# Conversation Handler para contato
contact_conv = ConversationHandler(
    entry_points=[CommandHandler('contato', contact_start)],
    states={
        CONTACT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, contact_name)],
        CONTACT_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, contact_message)],
    },
    fallbacks=[CommandHandler('cancelar', contact_cancel)],
)