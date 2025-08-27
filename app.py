#!/usr/bin/env python3
"""
🔧 APP.PY DEFINITIVO - Zero Race Conditions
WSGI entrypoint para Gunicorn: app:app
"""

import os
import logging
from unified_launcher_definitivo import create_integrated_app

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 🔥 VARIÁVEL GLOBAL PARA GUNICORN
app = create_integrated_app()
logger.info("✅ [APP DEFINITIVO] Aplicação integrada criada")

# Health endpoint para diagnóstico
@app.route('/_wsgi_health')
def _wsgi_health():
    return {
        "status": "definitivo_ok",
        "bot_enabled": bool(os.environ.get('TELEGRAM_TOKEN')),
        "pid": os.getpid(),
        "launcher": "unified_definitivo"
    }, 200

if __name__ == '__main__':
    # Standalone mode
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 [APP DEFINITIVO] Rodando em porta {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
