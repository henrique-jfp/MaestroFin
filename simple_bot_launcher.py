#!/usr/bin/env python3
"""
🤖 BOT LAUNCHER SIMPLES - Thread Principal Fix
Executa o bot corretamente resolvendo problema set_wakeup_fd
"""

import os
import logging
import sys
import signal

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def disable_signal_handling():
    """Desabilita signal handling problemático"""
    try:
        # Desabilitar sinais que causam problema em threads
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        signal.signal(signal.SIGTERM, signal.SIG_DFL)
        logger.info("✅ Signal handling desabilitado")
    except Exception as e:
        logger.warning(f"⚠️ Não foi possível desabilitar signals: {e}")

def main():
    """Executa o bot com correções para ambiente de produção"""
    logger.info("🚀 SIMPLE BOT LAUNCHER - Iniciando...")
    
    # Verificar ambiente
    is_render = bool(os.environ.get('RENDER_SERVICE_NAME'))
    
    if is_render:
        logger.info("🏭 Ambiente de produção detectado - Render")
        # Desabilitar signal handling problemático
        disable_signal_handling()
    else:
        logger.info("🏠 Ambiente de desenvolvimento detectado")
    
    try:
        logger.info("🤖 Importando e configurando bot...")
        
        # Importar bot
        from bot import create_application
        
        # Criar aplicação
        application = create_application()
        logger.info("✅ Bot configurado com sucesso")
        
        # Configurar polling apropriado para ambiente
        if is_render:
            logger.info("🎯 Iniciando polling para produção...")
            application.run_polling(
                poll_interval=2.0,
                timeout=20,
                bootstrap_retries=3,
                read_timeout=10,
                write_timeout=10,
                connect_timeout=10,
                pool_timeout=20,
                drop_pending_updates=True,
                close_loop=False,
                stop_signals=()  # Sem sinais para evitar set_wakeup_fd
            )
        else:
            logger.info("🎯 Iniciando polling para desenvolvimento...")
            application.run_polling()
            
        logger.info("Bot foi encerrado.")
        
    except ImportError as e:
        logger.error(f"❌ Erro de import: {e}")
        sys.exit(1)
        
    except Exception as e:
        logger.error(f"❌ Erro no bot: {e}", exc_info=True)
        if "set_wakeup_fd" in str(e):
            logger.error("🔧 PROBLEMA IDENTIFICADO: set_wakeup_fd")
            logger.error("💡 SOLUÇÃO: Execute em thread principal ou use webhook")
        sys.exit(1)

if __name__ == '__main__':
    main()
