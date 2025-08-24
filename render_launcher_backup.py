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
print("� Configurando ambiente Render...")
        setup_analytics_postgresql()
        
        print("📊 Carregando Dashboard Analytics...")
        from analytics.dashboard_app import app DASHBOARD - RENDER DEPLOY
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
        # 🚨 TESTE OCR NO RENDER
        print("� Testando OCR no Render...")
        test_ocr_render()
        
        print("�📊 Carregando Dashboard Analytics...")
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

def test_ocr_render():
    """🚨 TESTE ESPECÍFICO OCR PARA RENDER"""
    print("🔧 Testando configuração OCR...")
    
    # Testar variáveis de ambiente
    google_app_creds = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    google_json_creds = os.environ.get('GOOGLE_VISION_CREDENTIALS_JSON')
    gemini_key = os.environ.get('GEMINI_API_KEY')
    
    print(f"📋 GOOGLE_APPLICATION_CREDENTIALS: {'✅' if google_app_creds else '❌'}")
    print(f"📋 GOOGLE_VISION_CREDENTIALS_JSON: {'✅' if google_json_creds else '❌'}")
    print(f"📋 GEMINI_API_KEY: {'✅' if gemini_key else '❌'}")
    
    # Testar configuração de credenciais
    if google_json_creds:
        try:
            import tempfile
            import json
            
            temp_dir = tempfile.gettempdir()
            temp_creds_file = os.path.join(temp_dir, 'google_vision_render_test.json')
            
            with open(temp_creds_file, 'w') as f:
                f.write(google_json_creds)
            
            # Verificar se é JSON válido
            with open(temp_creds_file, 'r') as f:
                creds_data = json.load(f)
            
            print(f"✅ JSON Credenciais válido: projeto {creds_data.get('project_id', 'N/A')}")
            
            # Configurar variável
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = temp_creds_file
            
            # Testar cliente Google Vision
            from google.cloud import vision
            client = vision.ImageAnnotatorClient()
            print("✅ Cliente Google Vision criado com sucesso!")
            
        except Exception as e:
            print(f"❌ Erro teste OCR: {e}")
    
    # Testar Gemini
    if gemini_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            print("✅ Gemini configurado com sucesso!")
        except Exception as e:
            print(f"❌ Erro Gemini: {e}")
    
    print("🔧 Teste OCR concluído!")

def setup_analytics_postgresql():
    """🚀 Configura Analytics PostgreSQL no Render"""
    print("🔧 Configurando Analytics PostgreSQL...")
    
    try:
        # Testar se PostgreSQL está disponível
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            print("❌ DATABASE_URL não configurado")
            return
            
        print(f"✅ DATABASE_URL configurado")
        
        # Importar e inicializar analytics PostgreSQL
        from analytics.bot_analytics_postgresql import get_analytics
        pg_analytics = get_analytics()
        
        if pg_analytics.Session:
            print("✅ Analytics PostgreSQL inicializado")
            
            # Criar dados sintéticos na primeira execução
            stats = pg_analytics.get_daily_stats()
            if stats.get('total_commands', 0) == 0:
                print("📊 Primeira execução - criando dados sintéticos...")
                from migrate_analytics_postgresql import create_synthetic_data
                create_synthetic_data(pg_analytics)
                print("✅ Dados sintéticos criados!")
            else:
                print(f"📊 Analytics ativo: {stats.get('total_commands', 0)} comandos registrados")
        else:
            print("❌ Falha ao inicializar Analytics PostgreSQL")
            
    except Exception as e:
        print(f"❌ Erro configurando Analytics PostgreSQL: {e}")

if __name__ == '__main__':
    main()
