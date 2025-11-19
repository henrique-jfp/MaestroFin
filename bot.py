import logging
import warnings
import os
from datetime import time, datetime
from telegram.warnings import PTBUserWarning
from flask import Flask, jsonify

# Configuração inicial de logging e warnings
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
warnings.filterwarnings("ignore", category=PTBUserWarning)
logger = logging.getLogger(__name__)

# --- CARREGAMENTO DE MÓDULOS ESSENCIAIS ---
try:
    from secret_loader import setup_environment
    setup_environment()
    logger.info("✅ Secret Files carregado com sucesso")
except ImportError:
    logger.warning("⚠️ secret_loader não encontrado")

import config
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ConversationHandler, ApplicationBuilder
from database.database import get_db, popular_dados_iniciais, criar_tabelas
from models import *
from jobs import configurar_jobs

# --- IMPORTS DOS HANDLERS ---
from gerente_financeiro.handlers import create_gerente_conversation_handler, help_command, help_callback, cancel
# ... (outros handlers que você precisa)

# 🏦 OPEN FINANCE OAUTH (Nova Arquitetura)
try:
    from gerente_financeiro.open_finance_oauth_handler import get_open_finance_handlers
    OPEN_FINANCE_OAUTH_ENABLED = True
    logger.info("✅ Módulo Open Finance OAuth carregado.")
except Exception as e:
    OPEN_FINANCE_OAUTH_ENABLED = False
    logger.error(f"❌ Open Finance OAuth não disponível: {e}", exc_info=True)


def register_handlers(application: Application):
    """Registra todos os handlers do bot."""
    
    # Handlers principais
    application.add_handler(CommandHandler("start", help_command)) # /start agora mostra a ajuda
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(help_callback, pattern="^help_"))
    
    # Conversation Handlers
    application.add_handler(create_gerente_conversation_handler())
    # ... (adicione outros conversation handlers aqui)

    # Handlers do Open Finance
    if OPEN_FINANCE_OAUTH_ENABLED:
        try:
            of_handlers = get_open_finance_handlers()
            for handler in of_handlers:
                application.add_handler(handler)
            logger.info("✅ Handlers do novo módulo Open Finance registrados.")
        except Exception as e:
            logger.error(f"❌ Erro ao registrar handlers do Open Finance: {e}", exc_info=True)

    logger.info("Todos os handlers foram registrados.")


def create_application():
    """Cria e configura a aplicação do bot."""
    if not config.TELEGRAM_TOKEN:
        logger.critical("❌ Token do Telegram não configurado!")
        raise ValueError("Token do Telegram não configurado.")

    try:
        criar_tabelas()
        db = next(get_db())
        popular_dados_iniciais(db)
        db.close()
        logger.info("✅ Banco de dados inicializado.")
    except Exception as e:
        logger.critical(f"❌ Falha crítica na inicialização do banco de dados: {e}")
        raise

    application = ApplicationBuilder().token(config.TELEGRAM_TOKEN).build()
    
    register_handlers(application)
    
    job_queue = application.job_queue
    configurar_jobs(job_queue)
    
    return application

# O entry point principal agora seria o launcher.py, este arquivo define a criação da app.
