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

# Variáveis globais
bot_application = None
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
update_queue = queue.Queue()
executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="webhook-")

def process_updates_worker():
    """Worker dedicado para processar updates - roda em background"""
    logger.info("🔄 Worker de updates iniciado")
    
    while True:
        try:
            # Pegar update da queue (bloqueia até ter um)
            update = update_queue.get(timeout=60)  # Timeout de 60s
            
            if update is None:  # Sinal para parar
                logger.info("🛑 Worker de updates parando")
                break
                
            logger.info("⚡ Processando update em worker dedicado")
            
            # Criar loop isolado para este update
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # Processar update
                loop.run_until_complete(bot_application.process_update(update))
                logger.info("✅ Update processado com sucesso pelo worker")
                
            except Exception as e:
                logger.error(f"❌ Erro no worker: {e}")
                # Log do erro mas continua processando outros updates
                
            finally:
                loop.close()
                update_queue.task_done()
                
        except queue.Empty:
            # Timeout normal - continua executando
            continue
        except Exception as e:
            logger.error(f"❌ Erro crítico no worker: {e}")
            # Continua executando mesmo com erro

def setup_bot_webhook_render(flask_app):
    """Configuração de webhook otimizada para Render"""
    global bot_application
    
    if not TELEGRAM_TOKEN:
        logger.error("❌ TELEGRAM_TOKEN não configurado")
        return flask_app
    
    try:
        logger.info("🚀 Configurando bot webhook RENDER-OPTIMIZED...")
        
        # Importar e criar aplicação do bot
        from bot import create_application
        bot_application = create_application()
        
        # Inicializar bot de forma síncrona (mais estável no Render)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(bot_application.initialize())
            logger.info("✅ Bot inicializado (Render Mode)")
        finally:
            loop.close()
        
        # ✅ INICIAR WORKER EM BACKGROUND
        worker_thread = threading.Thread(target=process_updates_worker, daemon=True)
        worker_thread.start()
        logger.info("🔄 Worker de updates ativo")
        
        # Rota webhook OTIMIZADA
        @flask_app.route(f'/webhook/{TELEGRAM_TOKEN}', methods=['POST'])
        def webhook():
            """Webhook otimizado para Render - apenas adiciona à queue"""
            try:
                update_data = request.get_json()
                
                if update_data:
                    logger.info("📨 Update recebido via webhook")
                    
                    # Converter para objeto Update
                    update = Update.de_json(update_data, bot_application.bot)
                    
                    # ✅ SOLUÇÃO RENDER: Apenas adicionar à queue (super rápido)
                    try:
                        update_queue.put_nowait(update)
                        logger.info("⚡ Update adicionado à queue (processamento em background)")
                        
                    except queue.Full:
                        logger.warning("⚠️ Queue cheia, descartando update")
                    
                return "OK", 200
                
            except Exception as e:
                logger.error(f"❌ Erro no webhook: {e}")
                return "ERROR", 500
        
        # Rota para configurar webhook
        @flask_app.route('/set_webhook', methods=['GET', 'POST'])
        def set_webhook():
            """Configura webhook do Telegram"""
            try:
                base_url = os.environ.get('RENDER_EXTERNAL_URL', 'https://maestrofin-unified.onrender.com')
                webhook_url = f"{base_url}/webhook/{TELEGRAM_TOKEN}"
                
                logger.info(f"🔧 Configurando webhook: {webhook_url}")
                
                import requests
                response = requests.post(
                    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook",
                    data={'url': webhook_url},
                    timeout=10
                )
                result = response.json()
                
                if result.get('ok'):
                    return f"""
                    <!DOCTYPE html>
                    <html>
                    <head><title>✅ Webhook Render Mode</title></head>
                    <body style="font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px;">
                        <h2 style="color: green;">✅ Webhook Configurado (Render Mode)!</h2>
                        <p><strong>URL:</strong> <code>{webhook_url}</code></p>
                        <p><strong>Status:</strong> ✅ Ativo com worker dedicado</p>
                        <p><strong>Modo:</strong> 🔄 Queue-based processing</p>
                        <hr>
                        <h3>🧪 Teste Agora:</h3>
                        <ol>
                            <li>Digite <code>/help</code> no bot</li>
                            <li>Aguarde 2-3 segundos</li>
                            <li>Deve funcionar perfeitamente!</li>
                        </ol>
                        <p><a href="/bot_status" style="color: blue;">📊 Status do Bot</a></p>
                        <p><a href="/" style="color: blue;">🏠 Dashboard</a></p>
                    </body>
                    </html>
                    """, 200
                else:
                    return f"❌ Erro: {result.get('description', 'Desconhecido')}", 500
                    
            except Exception as e:
                logger.error(f"❌ Erro ao configurar webhook: {e}")
                return f"❌ Erro: {e}", 500
        
        # Status do bot
        @flask_app.route('/bot_status', methods=['GET'])
        def bot_status():
            """Status otimizado"""
            queue_size = update_queue.qsize()
            return f"""
            <!DOCTYPE html>
            <html>
            <head><title>🤖 Bot Status (Render Mode)</title></head>
            <body style="font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px;">
                <h2 style="color: green;">🤖 Bot Status - Render Mode</h2>
                <p>✅ Bot configurado: <strong>Sim</strong></p>
                <p>🔄 Worker ativo: <strong>Sim</strong></p>
                <p>📬 Updates na queue: <strong>{queue_size}</strong></p>
                <p>⚡ Modo: <strong>Background Processing</strong></p>
                
                <h3>🧪 Teste Rápido</h3>
                <p>Digite <code>/help</code> no bot - deve funcionar!</p>
                
                <p><a href="/set_webhook" style="color: blue;">🔧 Reconfigurar Webhook</a></p>
                <p><a href="/" style="color: blue;">🏠 Dashboard</a></p>
            </body>
            </html>
            """, 200
        
        logger.info("✅ Webhook Render configurado com sucesso")
        return flask_app
        
    except Exception as e:
        logger.error(f"❌ Erro na configuração: {e}")
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
