"""
🔧 DOCUMENT HANDLER ADDON - Handler genérico para documentos
Permite OCR de fotos e documentos enviados diretamente ao bot
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters
from gerente_financeiro.ocr_handler import ocr_iniciar_como_subprocesso

logger = logging.getLogger(__name__)

async def handle_generic_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler genérico para documentos/fotos enviados diretamente
    Redireciona automaticamente para o sistema OCR
    """
    try:
        user = update.effective_user
        logger.info(f"📄 Documento recebido de {user.username or user.first_name}")
        
        # Verificar se é foto ou documento
        is_photo = bool(update.message.photo)
        is_document = bool(update.message.document)
        
        if is_photo:
            logger.info("📸 Tipo: Foto - redirecionando para OCR")
            await update.message.reply_text("📸 Foto recebida! Processando com OCR...")
        elif is_document:
            logger.info("📎 Tipo: Documento - redirecionando para OCR")
            await update.message.reply_text("📎 Documento recebido! Processando com OCR...")
        else:
            # Não deveria acontecer, mas por segurança
            await update.message.reply_text("❌ Tipo de arquivo não suportado")
            return
        
        # Chamar diretamente a função OCR
        await ocr_iniciar_como_subprocesso(update, context)
        
    except Exception as e:
        logger.error(f"❌ Erro no handler genérico de documentos: {e}")
        await update.message.reply_text(
            "❌ Erro ao processar documento. Tente usar o comando /extrato e envie o arquivo novamente."
        )

# Criar handlers para fotos e documentos
def create_document_handlers():
    """
    Cria os handlers para documentos e fotos
    """
    return [
        MessageHandler(filters.PHOTO, handle_generic_document),
        MessageHandler(filters.Document.ALL, handle_generic_document)
    ]

logger.info("✅ Document Handler Addon carregado")
