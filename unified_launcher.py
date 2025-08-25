#!/usr/bin/env python3
"""
🔧 UNIFIED LAUNCHER - Roda bot + dashboard no mesmo processo (Render Free)
Solução para plano gratuito do Render que não permite Background Workers
"""

import os
import logging
import threading
import time
from multiprocessing import Process

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_bot():
    """Executa o bot do Telegram"""
    try:
        logger.info("🤖 Iniciando bot do Telegram...")
        import bot
        bot.main()
    except Exception as e:
        logger.error(f"❌ Erro no bot: {e}")
        # Reiniciar bot em caso de erro
        time.sleep(5)
        run_bot()

def run_dashboard():
    """Executa o dashboard Flask"""
    try:
        logger.info("🌐 Iniciando dashboard...")
        from analytics.dashboard_app import app
        
        # Usar porta do Render ou 5000 como fallback
        port = int(os.environ.get('PORT', 5000))
        
        app.run(
            host='0.0.0.0',
            port=port,
            debug=False,  # Desabilitar debug em produção
            use_reloader=False  # Evitar conflitos com threading
        )
    except Exception as e:
        logger.error(f"❌ Erro no dashboard: {e}")
        time.sleep(5)
        run_dashboard()

def main():
    """Função principal que inicia bot e dashboard simultaneamente"""
    logger.info("🚀 UNIFIED LAUNCHER - Iniciando sistema completo...")
    
    # Verificar se é ambiente de produção
    is_production = os.environ.get('RENDER_SERVICE_NAME') is not None
    
    if is_production:
        logger.info("🏭 Ambiente de produção detectado (Render)")
        
        # Em produção, usar threading para rodar ambos
        bot_thread = threading.Thread(target=run_bot, daemon=True)
        dashboard_thread = threading.Thread(target=run_dashboard, daemon=False)
        
        # Iniciar bot em background
        bot_thread.start()
        logger.info("✅ Bot iniciado em thread separada")
        
        # Dashboard roda na thread principal (para manter o processo vivo)
        dashboard_thread.start()
        dashboard_thread.join()
        
    else:
        logger.info("🏠 Ambiente local detectado")
        
        # Localmente, usar processos separados
        bot_process = Process(target=run_bot)
        dashboard_process = Process(target=run_dashboard)
        
        try:
            bot_process.start()
            dashboard_process.start()
            
            logger.info("✅ Bot e Dashboard iniciados")
            
            # Aguardar ambos os processos
            bot_process.join()
            dashboard_process.join()
            
        except KeyboardInterrupt:
            logger.info("🛑 Parando serviços...")
            bot_process.terminate()
            dashboard_process.terminate()

if __name__ == '__main__':
    main()
