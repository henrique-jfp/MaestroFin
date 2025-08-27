#!/usr/bin/env python3
"""
🔧 UNIFIED LAUNCHER DEFINITIVO - Sem Race Conditions
"""

import os
import logging
import sys
import asyncio
import threading
import time
from flask import request, Flask
from telegram import Update
from telegram.ext import Application

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

###############################
# VARIÁVEIS GLOBAIS ROBUSTAS  #
###############################
bot_application: Application | None = None
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
event_loop: asyncio.AbstractEventLoop | None = None
loop_thread: threading.Thread | None = None

# 🔥 NOVO: Estado persistente em arquivo para sobreviver a restarts
BOT_STATUS_FILE = "/tmp/maestrofin_bot_status.txt"

def _get_bot_status():
    """Lê status do arquivo persistente"""
    try:
        if os.path.exists(BOT_STATUS_FILE):
            with open(BOT_STATUS_FILE, 'r') as f:
                return f.read().strip() == "true"
    except Exception:
        pass
    return False

def _set_bot_status(status: bool):
    """Salva status no arquivo persistente"""
    try:
        with open(BOT_STATUS_FILE, 'w') as f:
            f.write("true" if status else "false")
        logger.info(f"🔥 Status persistente atualizado: {status}")
    except Exception as e:
        logger.warning(f"⚠️ Erro ao salvar status: {e}")

def _start_loop_thread():
    """Inicia thread com loop único persistente se ainda não existir."""
    global event_loop, loop_thread
    if loop_thread and loop_thread.is_alive():
        return
    def runner():
        global event_loop
        event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(event_loop)
        logging.info("🔁 [unified] Loop assíncrono persistente iniciado")
        event_loop.run_forever()
    loop_thread = threading.Thread(target=runner, daemon=True, name="unified-loop")
    loop_thread.start()

async def _async_init_bot():
    """Inicializa bot e marca status como OK"""
    global bot_application
    try:
        if bot_application is None:
            from bot import create_application
            bot_application = create_application()
        if not getattr(bot_application, '_initialized', False):
            await bot_application.initialize()
        if not bot_application.running:
            await bot_application.start()
        
        # 🔥 CRUCIAL: Marcar status IMEDIATAMENTE
        _set_bot_status(True)
        logger.info("✅ [DEFINITIVO] Bot inicializado, startado e STATUS SALVO")
        
    except Exception as e:
        logger.error(f"❌ Erro na inicialização do bot: {e}")
        _set_bot_status(False)

def setup_bot_webhook(flask_app):
    """Configura bot com inicialização forçada"""
    if not TELEGRAM_TOKEN:
        logger.error("❌ TELEGRAM_TOKEN não configurado")
        return flask_app

    # Iniciar loop persistente
    _start_loop_thread()
    
    # 🔥 FORÇA inicialização IMEDIATAMENTE (sem aguardar)
    try:
        from analytics.migrations import run_bigint_migration
        run_bigint_migration()
    except Exception as e:
        logger.warning(f"⚠️ Migração BigInt falhou: {e}")
    
    # Agenda init mas NÃO aguarda (async)
    asyncio.run_coroutine_threadsafe(_async_init_bot(), event_loop)
    
    # 🔥 RETRY automático para garantir que bot suba
    def retry_init():
        time.sleep(5)  # Aguarda 5s
        if not _get_bot_status():
            logger.warning("🔄 Retry de inicialização do bot...")
            asyncio.run_coroutine_threadsafe(_async_init_bot(), event_loop)
    
    retry_thread = threading.Thread(target=retry_init, daemon=True)
    retry_thread.start()

    @flask_app.route(f'/webhook/{TELEGRAM_TOKEN}', methods=['POST'])
    def webhook():
        try:
            data = request.get_json()
            if data and bot_application and bot_application.running:
                update = Update.de_json(data, bot_application.bot)
                asyncio.run_coroutine_threadsafe(
                    bot_application.process_update(update), event_loop
                )
                logger.debug("📨 Update processado com sucesso")
            return "OK", 200
        except Exception as e:
            logger.error(f"❌ Erro webhook: {e}")
            return "ERROR", 500

    @flask_app.route('/set_webhook', methods=['GET'])
    def set_webhook():
        try:
            base_url = os.environ.get('RENDER_EXTERNAL_URL', 'https://maestrofin-unified.onrender.com')
            webhook_url = f"{base_url}/webhook/{TELEGRAM_TOKEN}"
            import requests
            resp = requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook",
                data={'url': webhook_url}, timeout=10
            ).json()
            return (f"Webhook configurado: {webhook_url}" if resp.get('ok') else str(resp)), 200 if resp.get('ok') else 500
        except Exception as e:
            return f"Erro: {e}", 500

    @flask_app.route('/bot_status', methods=['GET'])
    def bot_status():
        # 🔥 LÊ DO ARQUIVO PERSISTENTE
        bot_started = _get_bot_status()
        
        status = {
            "launcher": "unified_definitivo",
            "bot_started": bot_started,
            "loop_alive": bool(event_loop and event_loop.is_running()),
            "running": bool(bot_application and bot_application.running),
            "status_file": BOT_STATUS_FILE,
            "timestamp": time.time()
        }
        
        # DB Status
        try:
            from database import database as dbmod
            if hasattr(dbmod, 'is_db_available'):
                status["db_available"] = dbmod.is_db_available()
                status["db_error"] = dbmod.get_db_error()
        except Exception as e:
            status["db_available"] = False
            status["db_error"] = str(e)
        
        return status, 200

    @flask_app.route('/fix_bot', methods=['GET'])
    def fix_bot():
        try:
            asyncio.run_coroutine_threadsafe(_async_init_bot(), event_loop)
            return {"status": "reinit forçado"}, 200
        except Exception as e:
            return {"error": str(e)}, 500

    logger.info("✅ [DEFINITIVO] Webhook configurado com retry automático")
    return flask_app

def create_integrated_app():
    """Cria aplicação Flask com bot webhook integrado"""
    try:
        logger.info("🌐 Criando aplicação integrada DEFINITIVA...")
        
        # Importar dashboard Flask
        from analytics.dashboard_app import app
        
        # Integrar bot webhook
        app = setup_bot_webhook(app)
        
        logger.info("✅ Aplicação integrada DEFINITIVA criada")
        return app
        
    except Exception as e:
        logger.error(f"❌ Erro ao criar aplicação: {e}")
        # Fallback: apenas dashboard
        from analytics.dashboard_app import app
        return app

def main():
    """Função principal"""
    logger.info("🚀 UNIFIED LAUNCHER DEFINITIVO - Sem Race Conditions")
    
    # Resetar status no início
    _set_bot_status(False)
    
    try:
        app = create_integrated_app()
        port = int(os.environ.get('PORT', 5000))
        
        logger.info("🎯 Servidor DEFINITIVO iniciando...")
        
        app.run(
            host='0.0.0.0',
            port=port,
            debug=False,
            use_reloader=False,
            threaded=True
        )
        
    except Exception as e:
        logger.error(f"❌ Erro crítico: {e}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main()
