#!/usr/bin/env python3
"""
🔧 UNIFIED LAUNCHER - Dashboard Only (Render Fixed)
Launcher simplificado para funcionar no Render
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
    """Executa o dashboard Flask"""
    try:
        logger.info("🌐 Iniciando dashboard...")
        from analytics.dashboard_app import app
        
        port = int(os.environ.get('PORT', 5000))
        
        # Configurações para produção
        if os.environ.get('RENDER_SERVICE_NAME'):
            logger.info("🏭 Configuração Render - Dashboard")
            app.run(
                host='0.0.0.0',
                port=port,
                debug=False,
                use_reloader=False,
                threaded=True
            )
        else:
            logger.info("🏠 Configuração Local - Dashboard")
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
    logger.info("🚀 UNIFIED LAUNCHER - Iniciando sistema...")
    
    # Detectar ambiente
    is_render = bool(os.environ.get('RENDER_SERVICE_NAME'))
    
    if is_render:
        logger.info("🏭 Ambiente de produção detectado - Render")
        logger.info("🌐 Executando dashboard apenas (Bot via configuração manual)")
    else:
        logger.info("🏠 Ambiente de desenvolvimento detectado")
    
    # Executar dashboard
    run_dashboard()

if __name__ == '__main__':
    main()
