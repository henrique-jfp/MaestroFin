#!/usr/bin/env python3
"""
🌐 BOT WEBHOOK LAUNCHER - Versão Otimizada para Render
Executa bot via webhook integrado ao dashboard Flask
"""

import os
import logging
from flask import Flask, request
from telegram import Update
from telegram.ext import Application
import asyncio
import json

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configurações
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
RENDER_SERVICE_URL = os.environ.get('RENDER_EXTERNAL_URL', 'https://maestrofin-unified.onrender.com')

def create_webhook_app():
    """Cria aplicação Flask com webhook do Telegram integrado"""
    
    # Importar dashboard
    from analytics.dashboard_app import app as dashboard_app
    
    # Importar e configurar bot
    from bot import create_application
    bot_application = create_application()
    
    @dashboard_app.route(f'/webhook/{TELEGRAM_TOKEN}', methods=['POST'])
    async def webhook():
        """Processa updates do Telegram via webhook"""
        try:
            # Obter update do Telegram
            update_data = request.get_json()
            logger.info(f"📨 Webhook recebido: {update_data}")
            
            # Converter para objeto Update
            update = Update.de_json(update_data, bot_application.bot)
            
            # Processar update
            await bot_application.process_update(update)
            
            return "OK", 200
            
        except Exception as e:
            logger.error(f"❌ Erro no webhook: {e}")
            return "ERROR", 500
    
    @dashboard_app.route('/set_webhook', methods=['GET'])
    async def set_webhook():
        """Configura webhook do Telegram"""
        try:
            webhook_url = f"{RENDER_SERVICE_URL}/webhook/{TELEGRAM_TOKEN}"
            
            # Configurar webhook
            success = await bot_application.bot.set_webhook(
                url=webhook_url,
                drop_pending_updates=True,
                allowed_updates=['message', 'callback_query', 'inline_query']
            )
            
            if success:
                logger.info(f"✅ Webhook configurado: {webhook_url}")
                return f"Webhook configurado: {webhook_url}", 200
            else:
                logger.error("❌ Falha ao configurar webhook")
                return "Falha ao configurar webhook", 500
                
        except Exception as e:
            logger.error(f"❌ Erro ao configurar webhook: {e}")
            return f"Erro: {e}", 500
    
    @dashboard_app.route('/bot_status', methods=['GET'])
    async def bot_status():
        """Verifica status do bot"""
        try:
            bot_info = await bot_application.bot.get_me()
            webhook_info = await bot_application.bot.get_webhook_info()
            
            status = {
                'bot_username': bot_info.username,
                'bot_id': bot_info.id,
                'webhook_url': webhook_info.url,
                'pending_updates': webhook_info.pending_update_count,
                'status': 'active' if webhook_info.url else 'inactive'
            }
            
            return json.dumps(status, indent=2), 200, {'Content-Type': 'application/json'}
            
        except Exception as e:
            logger.error(f"❌ Erro ao verificar status: {e}")
            return f"Erro: {e}", 500
    
    return dashboard_app

def main():
    """Função principal"""
    logger.info("🚀 WEBHOOK LAUNCHER - Iniciando sistema...")
    
    if not TELEGRAM_TOKEN:
        logger.error("❌ TELEGRAM_TOKEN não configurado")
        return
    
    try:
        # Criar aplicação com webhook
        app = create_webhook_app()
        
        # Configurar porta
        port = int(os.environ.get('PORT', 5000))
        
        logger.info("🌐 Iniciando servidor Flask com webhook integrado...")
        logger.info(f"📡 Webhook será disponível em: /webhook/{TELEGRAM_TOKEN}")
        logger.info(f"⚙️ Configure webhook via: /set_webhook")
        logger.info(f"📊 Status do bot via: /bot_status")
        
        # Executar servidor
        app.run(
            host='0.0.0.0',
            port=port,
            debug=False,
            use_reloader=False,
            threaded=True
        )
        
    except Exception as e:
        logger.error(f"❌ Erro no webhook launcher: {e}")

if __name__ == '__main__':
    main()
