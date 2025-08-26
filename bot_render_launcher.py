#!/usr/bin/env python3
"""
🤖 BOT RENDER LAUNCHER - Solução para set_wakeup_fd
Launcher que contorna problema de thread principal no Render
"""

import os
import logging
import sys
import asyncio
import signal

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_render_environment():
    """Configura ambiente específico para Render"""
    try:
        # Desabilitar sinais problemáticos no Render
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        logger.info("✅ Sinais desabilitados para Render")
    except Exception as e:
        logger.warning(f"⚠️ Não foi possível desabilitar sinais: {e}")

async def run_bot_async():
    """Executa bot usando asyncio em vez de threading"""
    try:
        logger.info("🤖 Configurando bot para execução async...")
        
        # Importar bot
        from bot import create_application
        
        # Criar aplicação
        application = create_application()
        logger.info("✅ Bot configurado com sucesso")
        
        # Configurar para uso async
        async with application:
            logger.info("🎯 Iniciando bot com configuração async...")
            
            # Inicializar aplicação
            await application.initialize()
            await application.start()
            
            # Configurar webhook ou polling baseado no ambiente
            if os.environ.get('RENDER_EXTERNAL_URL'):
                # Webhook para Render
                webhook_url = f"{os.environ.get('RENDER_EXTERNAL_URL')}/webhook"
                logger.info(f"📡 Configurando webhook: {webhook_url}")
                
                await application.bot.set_webhook(
                    url=webhook_url,
                    allowed_updates=['message', 'callback_query']
                )
                
                # Manter bot ativo
                logger.info("🔄 Bot ativo via webhook...")
                while True:
                    await asyncio.sleep(60)  # Manter vivo
                    
            else:
                # Polling para local/desenvolvimento
                logger.info("🔄 Iniciando polling...")
                await application.updater.start_polling()
                
                # Manter rodando
                await asyncio.Event().wait()
                
    except Exception as e:
        logger.error(f"❌ Erro no bot async: {e}", exc_info=True)
        raise

def main():
    """Função principal com configuração async"""
    logger.info("🚀 BOT RENDER LAUNCHER - Iniciando...")
    
    # Detectar ambiente
    is_render = bool(os.environ.get('RENDER_SERVICE_NAME'))
    
    if is_render:
        logger.info("🏭 Ambiente Render detectado")
        setup_render_environment()
    else:
        logger.info("🏠 Ambiente local detectado")
    
    try:
        # Executar bot usando asyncio
        logger.info("🎯 Iniciando bot via asyncio...")
        asyncio.run(run_bot_async())
        
    except KeyboardInterrupt:
        logger.info("🛑 Bot interrompido pelo usuário")
    except Exception as e:
        logger.error(f"❌ Erro crítico: {e}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main()
