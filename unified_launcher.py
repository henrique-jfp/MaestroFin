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

async def run_bot_async():
    """Executa o bot do Telegram de forma assíncrona e não bloqueante."""
    try:
        from bot import application  # Supondo que 'application' seja o seu ApplicationBuilder
        logger.info("🤖 Configurando o bot para execução assíncrona...")
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        logger.info("✅ Bot está online e recebendo updates.")
        # Mantém a função rodando para sempre
        while True:
            await asyncio.sleep(3600) # Dorme por 1h, apenas para manter a corrotina viva
    except Exception as e:
        logger.error(f"❌ Erro crítico no loop do bot: {e}", exc_info=True)

def start_bot_thread():
    """Inicia o loop de eventos do asyncio para o bot em uma nova thread."""
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_bot_async())

def run_bot_process():
    """Executa o bot do Telegram em um processo separado (para dev local)."""
    logger.info("🤖 Iniciando bot do Telegram em processo separado...")
    import bot
    bot.main()

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
        logger.error(f"❌ Erro no dashboard: {e}", exc_info=True)

def main():
    """Função principal que inicia bot e dashboard simultaneamente"""
    logger.info("🚀 UNIFIED LAUNCHER - Iniciando sistema completo...")
    
    # Verificar se é ambiente de produção
    is_production = os.environ.get('RENDER_SERVICE_NAME') is not None
    
    if is_production:
        logger.info("🏭 Ambiente de produção detectado (Render)")
        
        # Em produção, usar threading para rodar ambos
        bot_thread = threading.Thread(target=start_bot_thread, daemon=True)
        dashboard_thread = threading.Thread(target=run_dashboard, daemon=True) # daemon=True para encerrar com o principal
        
        # Iniciar bot em background
        bot_thread.start()
        logger.info("✅ Bot iniciado em thread separada")
        
        # Dashboard roda na thread principal (para manter o processo vivo)
        dashboard_thread.start()
        
        # Mantém a thread principal viva, monitorando as outras
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("🛑 Encerrando launcher unificado...")
        
    else:
        logger.info("🏠 Ambiente local detectado")
        
        # Localmente, usar processos separados para melhor isolamento
        bot_process = Process(target=run_bot_process)
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
