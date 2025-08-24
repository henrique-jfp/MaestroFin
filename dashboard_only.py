#!/usr/bin/env python3
"""
🚀 DASHBOARD ONLY LAUNCHER for RAILWAY
Launcher exclusivo para dashboard - sem bot
"""

import os
import sys

print("\n" + "="*50)
print("╭──────────────────────────────────────────────╮")
print("│        📊 MAESTROFIN DASHBOARD 📊           │")
print("│         Railway Deploy - REDEPLOY           │")
print("│         " + "24/08/2025 - 15:30" + "                │")
print("╰──────────────────────────────────────────────╯")
print("="*50)

# Verificar dependências básicas
try:
    import flask
    print("✅ Flask encontrado")
except ImportError as e:
    print(f"❌ Flask faltando: {e}")
    sys.exit(1)

# Configurar paths
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

def main():
    """Função principal - roda apenas o dashboard"""
    try:
        print("📊 Iniciando Dashboard Analytics...")
        from analytics.dashboard_app import app
        
        port = int(os.getenv('PORT', 8080))
        host = '0.0.0.0'
        
        print(f"📊 Dashboard iniciando em {host}:{port}")
        print(f"📊 Template dir: {app.template_folder}")
        print(f"📊 Static dir: {app.static_folder}")
        
        # Verificar se templates existem
        template_file = os.path.join(app.template_folder, 'dashboard_analytics_clean.html')
        print(f"📊 Template existe: {os.path.exists(template_file)}")
        
        # Iniciar apenas o dashboard
        app.run(
            host=host, 
            port=port, 
            debug=False, 
            threaded=True, 
            use_reloader=False
        )
        
    except Exception as e:
        print(f"❌ Erro ao iniciar dashboard: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
