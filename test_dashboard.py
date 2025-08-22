#!/usr/bin/env python3
"""
Teste direto do dashboard
"""

import os
import sys

# Configurar paths
sys.path.insert(0, os.getcwd())

try:
    print("🔍 Testando imports...")
    from analytics.bot_analytics import analytics
    print("✅ Analytics importado!")
    
    from flask import Flask
    print("✅ Flask importado!")
    
    # Testar paths
    template_dir = os.path.join(os.getcwd(), 'templates')
    print(f"📁 Template dir: {template_dir}")
    print(f"📄 Template exists: {os.path.exists(os.path.join(template_dir, 'dashboard_analytics.html'))}")
    
    # Inicializar analytics
    analytics.init_database()
    print("✅ Database inicializada!")
    
    # Testar Flask app
    from analytics.dashboard_app import app
    print("✅ Flask app criada!")
    
    print("\n🚀 INICIANDO SERVIDOR DE TESTE...")
    app.run(host='localhost', port=5000, debug=True)
    
except Exception as e:
    print(f"❌ ERRO: {e}")
    import traceback
    traceback.print_exc()
