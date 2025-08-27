#!/usr/bin/env python3
"""
🔧 UNIFIED LAUNCHER - Dashboard + Bot Webhook (Render Optimized)
Solução integrada: Dashboard Flask + Bot via Webhook
"""

import os
import logging
import sys
import asyncio
import threading
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
# VARIÁVEIS GLOBAIS / LOOP    #
###############################
bot_application: Application | None = None
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
event_loop: asyncio.AbstractEventLoop | None = None
loop_thread: threading.Thread | None = None
bot_started = threading.Event()

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
    """Inicializa (initialize + start) dentro do loop persistente."""
    global bot_application
    if bot_application is None:
        from bot import create_application
        bot_application = create_application()
    if not getattr(bot_application, '_initialized', False):
        await bot_application.initialize()
    if not bot_application.running:
        await bot_application.start()
    bot_started.set()
    logging.info("✅ [unified] Bot inicializado e startado (loop persistente)")

def setup_bot_webhook(flask_app):
    """Configura bot com loop persistente (compat para deploys que invocam unified_launcher)."""
    if not TELEGRAM_TOKEN:
        logger.error("❌ TELEGRAM_TOKEN não configurado")
        return flask_app

    # Iniciar loop persistente
    _start_loop_thread()

    # Agendar init (uma vez)
    if not bot_started.is_set():
        try:
            from analytics.migrations import run_bigint_migration
            run_bigint_migration()
        except Exception as e:  # pragma: no cover
            logger.warning(f"⚠️ Migração BigInt falhou: {e}")
        asyncio.run_coroutine_threadsafe(_async_init_bot(), event_loop)

    @flask_app.route(f'/webhook/{TELEGRAM_TOKEN}', methods=['POST'])
    def webhook():
        try:
            data = request.get_json()
            if data and bot_application:
                update = Update.de_json(data, bot_application.bot)
                asyncio.run_coroutine_threadsafe(
                    bot_application.process_update(update), event_loop
                )
                logger.info("📨 Update agendado (unified persistente)")
            return "OK", 200
        except Exception as e:
            logger.error(f"❌ Erro webhook unified: {e}")
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
        from database import database as dbmod
        return {
            "launcher": "unified",
            "bot_started": bot_started.is_set(),
            "loop_alive": bool(event_loop and event_loop.is_running()),
            "running": bool(bot_application and bot_application.running),
            "db_available": dbmod.is_db_available(),
            "db_ready_bot": bool(getattr(bot_application, 'bot_data', {}).get('db_ready')) if bot_application else False,
        }, 200

    @flask_app.route('/db_status', methods=['GET'])
    def db_status():
        from database import database as dbmod
        return {
            "available": dbmod.is_db_available(),
        }, 200

    @flask_app.route('/fix_bot', methods=['GET'])
    def fix_bot():
        try:
            asyncio.run_coroutine_threadsafe(_async_init_bot(), event_loop)
            return {"status": "reinit agendado"}, 200
        except Exception as e:
            return {"error": str(e)}, 500

    logger.info("✅ [unified] Webhook + loop persistente configurados")
    return flask_app

def create_integrated_app():
    """Cria aplicação Flask com bot webhook integrado"""
    try:
        logger.info("🌐 Criando aplicação integrada...")
        
        # Importar dashboard Flask
        from analytics.dashboard_app import app
        
        # Integrar bot webhook
        app = setup_bot_webhook(app)
        
        logger.info("✅ Aplicação integrada criada")
        return app
        
    except Exception as e:
        logger.error(f"❌ Erro ao criar aplicação integrada: {e}")
        # Fallback: apenas dashboard
        from analytics.dashboard_app import app
        return app

def main():
    """Função principal"""
    logger.info("🚀 UNIFIED LAUNCHER - Dashboard + Bot Webhook...")
    
    # Detectar ambiente
    is_render = bool(os.environ.get('RENDER_SERVICE_NAME'))
    
    if is_render:
        logger.info("🏭 Ambiente Render - Modo integrado webhook")
    else:
        logger.info("🏠 Ambiente local - Modo integrado")
    
    try:
        # Criar aplicação integrada
        app = create_integrated_app()
        
        # Configurar porta
        port = int(os.environ.get('PORT', 5000))
        
        logger.info("🎯 Iniciando servidor integrado...")
        logger.info("📡 Dashboard: /")
        logger.info("🤖 Bot Status: /bot_status")
        logger.info("🔧 Webhook Config: /set_webhook")
        
        # Executar servidor
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
