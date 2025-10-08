#!/usr/bin/env python3
"""
🚀 MAESTRO FINANCEIRO - Launcher Principal para Render
Launcher unificado e otimizado para produção
"""

import os
import sys
import logging
import asyncio
from threading import Thread
import signal

# Configurar logging básico
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_environment():
    """Carrega variáveis de ambiente"""
    try:
        # Tentar carregar .env se existir localmente
        if os.path.exists('.env'):
            from dotenv import load_dotenv
            load_dotenv()
            logger.info("✅ Arquivo .env carregado")
        
        # Verificar variáveis essenciais
        required_vars = [
            'TELEGRAM_TOKEN',
            'DATABASE_URL'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            logger.error(f"❌ Variáveis de ambiente faltando: {missing_vars}")
            return False
        
        logger.info("✅ Todas as variáveis essenciais estão configuradas")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao carregar ambiente: {e}")
        return False

def start_telegram_bot():
    """Inicia o bot do Telegram"""
    try:
        logger.info("🤖 Iniciando bot do Telegram...")
        from bot import main
        asyncio.run(main())
        
    except Exception as e:
        logger.error(f"❌ Erro no bot do Telegram: {e}")
        sys.exit(1)

def start_dashboard():
    """Inicia o dashboard Flask"""
    try:
        logger.info("📊 Iniciando dashboard Flask...")
        from analytics.dashboard_app import app
        
        port = int(os.getenv('PORT', 10000))
        app.run(
            host='0.0.0.0',
            port=port,
            debug=False,
            use_reloader=False
        )
        
    except Exception as e:
        logger.error(f"❌ Erro no dashboard: {e}")
        sys.exit(1)

def signal_handler(signum, frame):
    """Handler para sinais de sistema"""
    logger.info("🛑 Sinal de parada recebido. Encerrando...")
    sys.exit(0)

def main():
    """Função principal"""
    logger.info("🚀 Iniciando Maestro Financeiro...")
    
    # Configurar handler de sinais
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Carregar ambiente
    if not load_environment():
        logger.error("❌ Falha ao carregar ambiente. Encerrando...")
        sys.exit(1)
    
    # Verificar modo de execução
    mode = os.getenv('RENDER_SERVICE_TYPE', 'web')
    
    if mode == 'web':
        # Modo web - rodar dashboard Flask
        logger.info("🌐 Modo WEB: Iniciando dashboard Flask")
        start_dashboard()
        
    elif mode == 'background':
        # Modo background - rodar bot Telegram
        logger.info("🤖 Modo BACKGROUND: Iniciando bot Telegram")
        start_telegram_bot()
        
    else:
        # Modo local - rodar ambos em threads separadas
        logger.info("🔄 Modo LOCAL: Iniciando bot e dashboard")
        
        # Thread para o bot
        bot_thread = Thread(target=start_telegram_bot, daemon=True)
        bot_thread.start()
        
        # Dashboard na thread principal
        start_dashboard()

if __name__ == "__main__":
    main()
