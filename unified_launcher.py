#!/usr/bin/env python3
"""
🔧 UNIFIED LAUNCHER - Bot + Dashboard no mesmo processo (Render Free)
"""

import os
import logging
import threading
import time

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_bot_safe():
    """Executa o bot com patch para threads e monitoramento"""
    logger.info("🤖 Iniciando bot em thread...")
    retry_count = 0
    max_retries = 3
    
    while retry_count < max_retries:
        try:
            # Patch para desabilitar signal handlers em threads
            from telegram.ext import Application
            
            original_run_polling = Application.run_polling
            
            def thread_safe_polling(self, *args, **kwargs):
                kwargs['stop_signals'] = []
                return original_run_polling(self, *args, **kwargs)

            Application.run_polling = thread_safe_polling
            
            # Executar bot
            import bot
            bot.main()
            break  # Se chegou aqui, não houve erro

        except Exception as e:
            retry_count += 1
            logger.error(f"❌ Erro no bot (tentativa {retry_count}/{max_retries}): {e}")
            
            if retry_count < max_retries:
                wait_time = retry_count * 5  # Backoff progressivo
                logger.info(f"⏳ Aguardando {wait_time}s antes de tentar novamente...")
                time.sleep(wait_time)
            else:
                logger.critical("💥 Bot falhou após todas as tentativas!")
                raise

def run_dashboard():
    """Executa o dashboard Flask com configuração otimizada"""
    try:
        logger.info("🌐 Iniciando dashboard...")
        from analytics.dashboard_app import app
        
        port = int(os.environ.get('PORT', 5000))
        
        # Configurações otimizadas para produção
        if os.environ.get('RENDER_SERVICE_NAME'):
            # Configuração Render
            app.run(
                host='0.0.0.0',
                port=port,
                debug=False,
                use_reloader=False,
                threaded=True
            )
        else:
            # Configuração local com debug
            app.run(
                host='0.0.0.0',
                port=port,
                debug=True,
                use_reloader=False,
                threaded=True
            )
    except Exception as e:
        logger.error(f"❌ Erro no dashboard: {e}", exc_info=True)

def main():
    """Função principal"""
    logger.info("🚀 UNIFIED LAUNCHER - Iniciando sistema...")
    
    is_production = os.environ.get('RENDER_SERVICE_NAME') is not None
    
    if is_production:
        logger.info("🏭 Ambiente de produção detectado")
        
        # Iniciar bot em thread separada
        bot_thread = threading.Thread(target=run_bot_safe, daemon=True)
        bot_thread.start()
        logger.info("✅ Bot iniciado em thread")
        
        # Dashboard na thread principal
        run_dashboard()
        
    else:
        logger.info("🏠 Ambiente local")
        from multiprocessing import Process
        
        try:
            bot_process = Process(target=lambda: __import__('bot').main())
            dashboard_process = Process(target=run_dashboard)
            
            bot_process.start()
            dashboard_process.start()
            
            logger.info("✅ Processos iniciados")
            
            bot_process.join()
            dashboard_process.join()
            
        except KeyboardInterrupt:
            logger.info("🛑 Parando...")
            bot_process.terminate()
            dashboard_process.terminate()

if __name__ == '__main__':
    main()
