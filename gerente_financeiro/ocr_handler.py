# gerente_financeiro/ocr_handler.py

import logging
import os
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

def setup_google_credentials():
    """
    Configura as credenciais do Google Vision API.
    Retorna True se configurado com sucesso, False caso contrário.
    """
    try:
        google_creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        if google_creds_path and os.path.exists(google_creds_path):
            logger.info("✅ GOOGLE_APPLICATION_CREDENTIALS configurado")
            return True
        else:
            logger.warning("⚠️ GOOGLE_APPLICATION_CREDENTIALS não configurado - funcionalidades OCR limitadas")
            return False
    except Exception as e:
        logger.error(f"❌ Erro ao configurar credenciais Google: {e}")
        return False

async def ocr_iniciar_como_subprocesso(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Função placeholder para iniciar OCR como subprocesso.
    """
    logger.info("OCR subprocess iniciado (placeholder)")
    await update.message.reply_text("� OCR não está disponível no momento. Use o modo manual.")

async def ocr_action_processor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Processa mensagens com imagens/PDFs para OCR.
    """
    try:
        # Placeholder - funcionalidade básica
        if update.message.photo:
            await update.message.reply_text(
                "📷 <b>OCR Temporariamente Indisponível</b>\n\n"
                "As funcionalidades de reconhecimento de imagem estão sendo atualizadas.\n"
                "Use o modo manual para registrar seus lançamentos.",
                parse_mode='HTML'
            )
        elif update.message.document and update.message.document.mime_type == "application/pdf":
            await update.message.reply_text(
                "📄 <b>OCR de PDF Temporariamente Indisponível</b>\n\n"
                "As funcionalidades de processamento de PDF estão sendo atualizadas.\n"
                "Use o modo manual para registrar seus lançamentos.",
                parse_mode='HTML'
            )
        else:
            await update.message.reply_text(
                "� <b>Tipo de arquivo não suportado</b>\n\n"
                "Envie uma foto ou PDF para processamento automático,\n"
                "ou use /lancamento para o modo manual.",
                parse_mode='HTML'
            )
    except Exception as e:
        logger.error(f"Erro no processamento OCR: {e}")
        await update.message.reply_text(
            "❌ Erro ao processar o arquivo. Tente novamente ou use o modo manual."
        )