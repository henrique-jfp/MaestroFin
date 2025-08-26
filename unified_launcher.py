#!/usr/bin/env python3
"""
🔧 UNIFIED LAUNCHER - Bot + Dashboard (Render Optimized)
Launcher inteligente que detecta o ambiente e executa o serviço apropriado
"""

import os
import logging
import sys
import asyncio
import threading
import time

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_bot_safe():
    """Executa o bot de forma segura com event loop"""
    import asyncio
    
    try:
        # Criar novo event loop para a thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        logger.info("🤖 Iniciando bot em thread dedicada...")
        from bot import main as bot_main
        bot_main()
        
    except Exception as e:
        logger.error(f"❌ Erro no bot: {e}")
        time.sleep(5)  # Esperar antes de tentar novamente

def run_dashboard():
    """Executa o dashboard Flask com configuração otimizada"""
    try:
        logger.info("🌐 Iniciando dashboard...")
        from analytics.dashboard_app import app
        
        port = int(os.environ.get('PORT', 5000))
        
        # Configurações otimizadas para produção
        if os.environ.get('RENDER_SERVICE_NAME'):
            logger.info("🏭 Configuração Render - Produção")
            app.run(
                host='0.0.0.0',
                port=port,
                debug=False,
                use_reloader=False,
                threaded=True
            )
        else:
            logger.info("🏠 Configuração Local - Desenvolvimento")
            app.run(
                host='0.0.0.0',
                port=port,
                debug=True,
                use_reloader=False,
                threaded=True
            )
    except Exception as e:
        logger.error(f"❌ Erro no dashboard: {e}", exc_info=True)
        sys.exit(1)

def run_unified():
    """Executa bot + dashboard em modo unificado"""
    logger.info("🔄 Modo unificado - Iniciando bot e dashboard...")
    
    # Iniciar bot em thread separada
    logger.info("🤖 Iniciando bot em thread...")
    bot_thread = threading.Thread(target=run_bot_safe, daemon=True)
    bot_thread.start()
    logger.info("✅ Bot iniciado em thread")
    
    # Aguardar um pouco para o bot inicializar
    time.sleep(2)
    
    # Iniciar dashboard no thread principal
    logger.info("🌐 Iniciando dashboard...")
    run_dashboard()

def main():
    """Função principal com detecção inteligente de modo"""
    logger.info("🚀 UNIFIED LAUNCHER - Iniciando sistema...")
    
    # Detectar ambiente
    is_render = bool(os.environ.get('RENDER_SERVICE_NAME'))
    mode = os.environ.get('MAESTROFIN_MODE', 'unified')
    
    if is_render:
        logger.info("🏭 Ambiente de produção detectado")
    else:
        logger.info("🏠 Ambiente de desenvolvimento detectado")
        
    logger.info(f"⚙️ Modo configurado: {mode}")
    
    # Executar baseado no modo
    if mode == 'bot':
        logger.info("🤖 Executando apenas bot...")
        run_bot_safe()
    elif mode == 'dashboard' or mode == 'web':
        logger.info("🌐 Executando apenas dashboard...")
        run_dashboard()
    elif mode == 'unified':
        logger.info("🔄 Executando modo unificado...")
        run_unified()
    else:
        logger.warning(f"⚠️ Modo desconhecido: {mode}, usando dashboard")
        run_dashboard()

if __name__ == '__main__':
    main()

import os
import logging
import sys

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_dashboard():
    """Executa o dashboard Flask com configuração otimizada"""
    try:
        logger.info("🌐 Iniciando dashboard...")
        from analytics.dashboard_app import app
        
        port = int(os.environ.get('PORT', 5000))
        
        # Configurações otimizadas para produção
        if os.environ.get('RENDER_SERVICE_NAME'):
            logger.info("🏭 Configuração Render - Dashboard apenas")
            app.run(
                host='0.0.0.0',
                port=port,
                debug=False,
                use_reloader=False,
                threaded=True
            )
        else:
            logger.info("🏠 Configuração Local - Dashboard com debug")
            app.run(
                host='0.0.0.0',
                port=port,
                debug=True,
                use_reloader=False,
                threaded=True
            )
    except Exception as e:
        logger.error(f"❌ Erro no dashboard: {e}", exc_info=True)
        sys.exit(1)

def main():
    """Função principal"""
    logger.info("🚀 UNIFIED LAUNCHER - Iniciando dashboard...")
    
    # Verificar se deve executar apenas dashboard
    mode = os.environ.get('MAESTROFIN_MODE', 'dashboard')
    is_production = os.environ.get('RENDER_SERVICE_NAME') is not None
    
    if is_production:
        logger.info("🏭 Ambiente de produção - Render")
        logger.info(f"📋 Modo: {mode}")
        
        if mode == 'dashboard' or mode == 'web':
            logger.info("� Executando apenas dashboard (modo web)")
            run_dashboard()
        else:
            logger.info("🤖 Modo bot detectado - redirecionando...")
            import bot
            bot.main()
    else:
        logger.info("🏠 Ambiente local - Dashboard apenas")
        run_dashboard()

if __name__ == '__main__':
    main()
