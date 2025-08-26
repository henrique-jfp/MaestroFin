#!/usr/bin/env python3
"""
🤖 BOT LAUNCHER DEDICADO - Execução Correta do Bot
Launcher especializado para executar o bot na thread principal
"""

import os
import logging
import sys

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Executa o bot na thread principal"""
    logger.info("🚀 BOT LAUNCHER - Iniciando bot...")
    
    # Verificar ambiente
    is_render = bool(os.environ.get('RENDER_SERVICE_NAME'))
    
    if is_render:
        logger.info("🏭 Ambiente de produção detectado - Render")
    else:
        logger.info("🏠 Ambiente de desenvolvimento detectado")
    
    try:
        # Importar e executar bot diretamente na thread principal
        logger.info("🤖 Importando bot...")
        from bot import run_bot
        
        logger.info("✅ Bot importado com sucesso")
        logger.info("🎯 Executando bot na thread principal...")
        
        # Executar bot (resolve problema set_wakeup_fd)
        run_bot()
        
    except ImportError as e:
        logger.error(f"❌ Erro de import do bot: {e}")
        logger.error("📁 Verificando se arquivo bot.py existe...")
        sys.exit(1)
        
    except Exception as e:
        logger.error(f"❌ Erro no bot: {e}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main()
