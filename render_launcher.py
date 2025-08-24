#!/usr/bin/env python3
"""
🎨 MAESTROFIN DASHBOARD - RENDER DEPLOY
Launcher otimizado para Render (gratuito)
"""

import os
import sys

print("\n" + "="*60)
print("╭────────────────────────────────────────────────────────╮")
print("│              🎼 MAESTROFIN DASHBOARD 🎼                │")
print("│                 🎨 Render Deploy                       │")
print("│               ⚡ Gratuito e Confiável                  │")
print("╰────────────────────────────────────────────────────────╯")
print("="*60)

# Verificar dependências
try:
    import flask
    from flask import Flask
    print("✅ Flask detectado")
except ImportError as e:
    print(f"❌ Flask não encontrado: {e}")
    print("📦 Instalando dependências...")
    os.system("pip install -r requirements.txt")
    import flask

# Configurações para Render
print("🔧 Configurando ambiente Render...")

def main():
    """Iniciar dashboard otimizado para Render"""
    try:
        print("📊 Carregando Dashboard Analytics...")
        from analytics.dashboard_app import app
        
        # Render usa PORT automaticamente
        port = int(os.environ.get('PORT', 10000))
        host = '0.0.0.0'
        
        print(f"🌐 Dashboard iniciando em {host}:{port}")
        print(f"📁 Template dir: {app.template_folder}")
        print(f"📁 Static dir: {app.static_folder}")
        
        # Verificações para Render
        template_path = os.path.join(app.template_folder, 'dashboard_analytics_clean.html')
        css_path = os.path.join(app.static_folder, 'dashboard_cyberpunk.css')
        
        print(f"✅ Template: {'OK' if os.path.exists(template_path) else 'ERRO'}")
        print(f"✅ CSS: {'OK' if os.path.exists(css_path) else 'ERRO'}")
        
        print("🚀 Iniciando servidor Flask...")
        print("🎨 Dashboard disponível no Render!")
        
        # Configuração otimizada para Render
        app.run(
            host=host,
            port=port,
            debug=False,           # Render = produção
            threaded=True,         # Suporte múltiplas conexões
            use_reloader=False     # Sem reload em produção
        )
        
    except Exception as e:
        print(f"❌ Erro ao iniciar: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
