#!/usr/bin/env python3
"""
🔧 APP.PY DEFINITIVO - Zero Race Conditions
"""

import os
from unified_launcher_definitivo import create_integrated_app

# Variável global para Gunicorn app:app
app = create_integrated_app()

if __name__ == '__main__':
    # Standalone mode
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 [APP DEFINITIVO] Rodando em porta {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
