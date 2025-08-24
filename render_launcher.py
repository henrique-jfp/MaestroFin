#!/usr/bin/env python3
"""
🎨 MAESTROFIN DASHBOARD - RENDER DEPLOY
Launcher otimizado para Render (gratuito)
"""

import os
import sys
import json

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
    """Função principal - inicia BOT + DASHBOARD no Render"""
    try:
        print("✅ Flask detectado")
        print("� Configurando ambiente Render...")
        
        # Testar OCR
        test_ocr()
        
        # 🚀 MIGRAR ANALYTICS PARA POSTGRESQL
        print("🔄 Configurando Analytics PostgreSQL...")
        setup_analytics_postgresql()
        
        # 🤖 INICIAR BOT TELEGRAM EM BACKGROUND
        print("🤖 Iniciando Bot Telegram...")
        import threading
        import subprocess
        import sys
        
        def run_bot():
            """Executa o bot Telegram em thread separada"""
            try:
                print("🚀 Bot Telegram iniciando...")
                # Importar e executar o bot
                import bot
                bot.main()
            except Exception as e:
                print(f"❌ Erro no Bot Telegram: {e}")
        
        # Iniciar bot em thread separada
        bot_thread = threading.Thread(target=run_bot, daemon=True)
        bot_thread.start()
        print("✅ Bot Telegram rodando em background!")
        
        print("📊 Carregando Dashboard Analytics...")
        from analytics.dashboard_app_render_fixed import app
        
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
        print("🤖 Bot Telegram ativo e processando mensagens!")
        
        # Iniciar Flask (bloqueia thread principal)
        app.run(host=host, port=port, debug=False, threaded=True)
        
    except Exception as e:
        print(f"❌ Erro crítico: {e}")
        import traceback
        traceback.print_exc()

def test_ocr():
    """Testa configuração OCR no Render com suporte a Secret Files"""
    print("� Testando OCR no Render...")
    
    try:
        print("🔧 Testando configuração OCR...")
        
        # Verificar métodos disponíveis de credenciais
        secret_file = '/etc/secrets/google_vision_credentials.json'
        env_var_json = os.getenv('GOOGLE_VISION_CREDENTIALS_JSON')
        env_var_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        
        print(f"📋 Secret File (/etc/secrets/...): {'✅' if os.path.exists(secret_file) else '❌'}")
        print(f"📋 GOOGLE_APPLICATION_CREDENTIALS: {'✅' if env_var_path else '❌'}")
        print(f"📋 GOOGLE_VISION_CREDENTIALS_JSON: {'✅' if env_var_json else '❌'}")
        
        gemini_key = os.getenv('GEMINI_API_KEY')
        print(f"📋 GEMINI_API_KEY: {'✅' if gemini_key else '❌'}")
        
        credentials_configured = False
        
        # Testar Secret Files (método mais seguro)
        if os.path.exists(secret_file):
            try:
                with open(secret_file, 'r') as f:
                    secret_data = json.load(f)
                project_id = secret_data.get('project_id', 'N/A')
                print(f"✅ Secret File válido: projeto {project_id}")
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = secret_file
                credentials_configured = True
            except Exception as e:
                print(f"❌ Erro no Secret File: {e}")
        
        # Fallback para variável de ambiente JSON
        elif env_var_json:
            try:
                import tempfile
                creds_data = json.loads(env_var_json)
                project_id = creds_data.get('project_id', 'N/A')
                print(f"✅ JSON Credenciais válido: projeto {project_id}")
                
                # Criar arquivo temporário
                temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
                json.dump(creds_data, temp_file)
                temp_file.close()
                
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = temp_file.name
                credentials_configured = True
            except Exception as e:
                print(f"❌ Erro JSON credenciais: {e}")
        
        # Testar Google Vision se credenciais configuradas
        if credentials_configured:
            try:
                from google.cloud import vision
                client = vision.ImageAnnotatorClient()
                print("✅ Cliente Google Vision criado com sucesso!")
            except Exception as e:
                print(f"❌ Erro Google Vision: {e}")
        
        # Testar Gemini
        if gemini_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=gemini_key)
                print("✅ Gemini configurado com sucesso!")
            except Exception as e:
                print(f"❌ Erro Gemini: {e}")
        
        print("🔧 Teste OCR concluído!")
        
    except Exception as e:
        print(f"❌ Erro no teste OCR: {e}")

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
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
