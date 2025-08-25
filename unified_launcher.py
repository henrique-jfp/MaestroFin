#!/usr/bin/env python3
"""
🔧 UNIFIED LAUNCHER - Roda bot + dashboard no mesmo processo (Render Free)
Solução para plano gratuito do Render que não permite Background Workers
"""

import asyncio
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

def run_bot_thread_safe():
    """
    Executa o bot do Telegram em uma thread, aplicando um patch para
    desabilitar os signal handlers que causam erro fora da thread principal.
    Esta é a abordagem correta para rodar em produção no Render Free Tier.
    """
    logger.info("🤖 Iniciando bot do Telegram em thread (modo de produção)...")
    try:
        # Monkey-patch para desabilitar os signal handlers no run_polling.
        # Isso é necessário para rodar em uma thread que não é a principal,
        # evitando o erro "ValueError: set_wakeup_fd only works in main thread".
        from telegram.ext import Application
        
        original_run_polling = Application.run_polling
        
        def thread_safe_run_polling(self, *args, **kwargs):
            logger.info("🔧 Aplicando patch para `run_polling` em thread.")
            # Força a desativação dos signal handlers, que só funcionam na thread principal.
            kwargs['stop_signals'] = []
            return original_run_polling(self, *args, **kwargs)

        Application.run_polling = thread_safe_run_polling
        logger.info("✅ Patch de `run_polling` aplicado com sucesso.")

        # Agora podemos chamar bot.main() com segurança, pois ele usará nossa versão corrigida.
        import bot
        bot.main()

    except Exception as e:
        logger.error(f"❌ Erro crítico ao iniciar o bot na thread: {e}", exc_info=True)

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
        bot_thread = threading.Thread(target=run_bot_thread_safe, daemon=True)
        bot_thread.start()
        logger.info("✅ Bot iniciado em thread separada")
        
        # O dashboard agora roda diretamente na thread principal.
        # Como app.run() é bloqueante, ele manterá o processo vivo
        # enquanto o bot roda na thread em segundo plano.
        run_dashboard()
        
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
