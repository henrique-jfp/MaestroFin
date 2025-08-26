#!/usr/bin/env python3
"""
🔧 LAUNCHER ESPECIALIZADO RENDER - Solução definitiva para webhook
Implementação específica para ambiente Render com threading otimizado
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

# ✅ SOLUÇÃO RENDER: Pool de threads dedicado
from concurrent.futures import ThreadPoolExecutor
import queue

# =====================
#   NOVA ARQUITETURA
# =====================
# 1 loop asyncio único e persistente em thread dedicada.
# Workers de fila não criam/fecham loops – usam run_coroutine_threadsafe.
# Isso elimina RuntimeError("Event loop is closed") em handlers.

event_loop: asyncio.AbstractEventLoop | None = None
loop_thread: threading.Thread | None = None
bot_started = threading.Event()

# Variáveis globais
bot_application: Application | None = None
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
update_queue = queue.Queue()
executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="webhook-")

def process_updates_worker():
    """Worker que retira updates da fila e agenda no loop persistente."""
    logger.info("🔄 Worker de updates iniciado (loop persistente)")
    while True:
        try:
            update = update_queue.get(timeout=60)
            if update is None:
                logger.info("🛑 Worker encerrado por sinal")
                break

            # Esperar bot inicializar
            if not bot_started.wait(timeout=30):
                logger.error("⚠️ Bot não inicializou em 30s – descartando update")
                update_queue.task_done()
                continue

            if not bot_application or not event_loop:
                logger.error("⚠️ Bot/loop ausentes – descartando update")
                update_queue.task_done()
                continue

            try:
                fut = asyncio.run_coroutine_threadsafe(
                    bot_application.process_update(update), event_loop
                )
                fut.result(timeout=60)  # processamento sequencial
                logger.info("✅ Update processado")
            except Exception as e:
                logger.error(f"❌ Erro processando update: {e}")
            finally:
                update_queue.task_done()
        except queue.Empty:
            continue
        except Exception as e:
            logger.error(f"❌ Erro crítico worker: {e}")

def _start_async_loop():
    """Thread alvo que mantém o loop rodando para toda a vida do processo."""
    global event_loop
    event_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(event_loop)
    logger.info("🔁 Loop assíncrono principal iniciado")
    event_loop.run_forever()


async def _async_init_bot():
    """Coroutine que cria e inicia a aplicação do bot dentro do loop persistente."""
    global bot_application
    from bot import create_application
    bot_application = create_application()
    await bot_application.initialize()
    await bot_application.start()
    bot_started.set()
    logger.info("✅ Bot inicializado e startado (loop persistente)")


def setup_bot_webhook_render(flask_app):
    """Configura webhook usando loop persistente."""
    if not TELEGRAM_TOKEN:
        logger.error("❌ TELEGRAM_TOKEN não configurado")
        return flask_app

    # Iniciar loop se ainda não
    global loop_thread
    if not loop_thread or not loop_thread.is_alive():
        loop_thread = threading.Thread(target=_start_async_loop, daemon=True)
        loop_thread.start()

    # Agendar inicialização do bot (uma vez)
    if not bot_started.is_set():
        # Rodar migração antes de startar bot para evitar erros de analytics
        try:
            from analytics.migrations import run_bigint_migration
            run_bigint_migration()
        except Exception as e:  # pragma: no cover
            logger.error(f"⚠️ Falha migração BigInt: {e}")

        # Schedule coroutine
        def schedule_init():
            try:
                asyncio.run_coroutine_threadsafe(_async_init_bot(), event_loop)
            except Exception as e:
                logger.error(f"Erro agendando init bot: {e}")
        schedule_init()

    # Iniciar worker fila
    worker_thread = threading.Thread(target=process_updates_worker, daemon=True)
    worker_thread.start()

    @flask_app.route(f'/webhook/{TELEGRAM_TOKEN}', methods=['POST'])
    def webhook():
        try:
            data = request.get_json()
            if data and bot_application:
                update = Update.de_json(data, bot_application.bot)
                try:
                    update_queue.put_nowait(update)
                    logger.info("📨 Update enfileirado")
                except queue.Full:
                    logger.warning("⚠️ Fila cheia – descartando update")
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
            if resp.get('ok'):
                return f"Webhook configurado: {webhook_url}", 200
            return f"Erro: {resp}", 500
        except Exception as e:
            return f"Erro: {e}", 500

    @flask_app.route('/bot_status')
    def bot_status():
        return {
            "bot_started": bot_started.is_set(),
            "queue_size": update_queue.qsize(),
            "loop_alive": bool(event_loop and event_loop.is_running()),
        }, 200

    @flask_app.route('/migrate_analytics')
    def migrate_analytics():
        try:
            from analytics.migrations import run_bigint_migration
            res = run_bigint_migration()
            return {"result": res}, 200
        except Exception as e:
            return {"error": str(e)}, 500

    logger.info("✅ Webhook + loop persistente configurados")
    return flask_app

def create_render_app():
    """Cria aplicação otimizada para Render"""
    try:
        logger.info("🏭 Criando aplicação RENDER-OPTIMIZED...")
        
        # Dashboard
        from analytics.dashboard_app import app
        
        # Integrar webhook otimizado
        app = setup_bot_webhook_render(app)
        
        logger.info("✅ Aplicação Render criada")
        return app
        
    except Exception as e:
        logger.error(f"❌ Erro: {e}")
        from analytics.dashboard_app import app
        return app

def main():
    """Launcher principal otimizado para Render"""
    logger.info("🚀 RENDER LAUNCHER - Webhook Otimizado Iniciando...")
    
    try:
        # Criar app otimizada
        app = create_render_app()
        
        # Configurar porta
        port = int(os.environ.get('PORT', 5000))
        
        logger.info("🎯 Servidor Render iniciando...")
        logger.info("📡 Dashboard: /")
        logger.info("🤖 Status: /bot_status")
        logger.info("🔧 Webhook: /set_webhook")
        logger.info("⚡ Modo: Background Queue Processing")
        
        # Executar com configurações otimizadas para Render
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
