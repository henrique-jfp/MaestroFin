#!/usr/bin/env python3
"""
🔧 UNIFIED LAUNCHER - Bot + Dashboard (Render Optimized)
Executa apenas dashboard no Render, bot separadamente
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
