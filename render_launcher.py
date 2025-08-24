#!/usr/bin/env python3
"""
🎨 MAESTROFIN RENDER LAUNCHER - CORRIGIDO
Inicializa bot Telegram (asyncio) + servidor Flask (Gunicorn) para produção
"""

import os
import sys
import json
import asyncio
import threading
import traceback
import logging

print("\n" + "="*60)
print("╭────────────────────────────────────────────────────────╮")
print("│              🎼 MAESTROFIN DASHBOARD 🎼                │")
print("│           🚀 Render Deploy - CORRIGIDO                │")
print("╰────────────────────────────────────────────────────────╯")
print("="*60)

def setup_credentials():
    """Configura credenciais do Google Cloud (Secret Files ou Env Var)"""
    print("🔧 Configurando credenciais Google Cloud...")
    
    try:
        secret_file = '/etc/secrets/google_vision_credentials.json'
        env_var_json = os.getenv('GOOGLE_VISION_CREDENTIALS_JSON')
        
        credentials_configured = False
        
        if os.path.exists(secret_file):
            try:
                with open(secret_file, 'r') as f:
                    secret_data = json.load(f)
                project_id = secret_data.get('project_id', 'N/A')
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = secret_file
                credentials_configured = True
                print(f"✅ Secret File configurado - Projeto: {project_id}")
            except Exception as e:
                print(f"❌ Erro ao ler Secret File: {e}")
        
        elif env_var_json:
            try:
                import tempfile
                creds_data = json.loads(env_var_json)
                temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
                json.dump(creds_data, temp_file)
                temp_file.close()
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = temp_file.name
                credentials_configured = True
                print("✅ Credenciais configuradas via variável de ambiente")
            except Exception as e:
                print(f"❌ Erro ao processar env var: {e}")
        
        if not credentials_configured:
            print("⚠️ Nenhuma credencial do Google Cloud configurada")
        
        # Testar conexão
        if credentials_configured:
            try:
                from google.cloud import vision
                client = vision.ImageAnnotatorClient()
                print("✅ Cliente Google Vision inicializado")
            except Exception as e:
                print(f"❌ Erro ao inicializar Google Vision: {e}")
                
    except Exception as e:
        print(f"❌ Erro na configuração de credenciais: {e}")

def setup_analytics():
    """Configura sistema de analytics PostgreSQL"""
    print("🔧 Configurando Analytics PostgreSQL...")
    
    try:
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            print("⚠️ DATABASE_URL não configurado")
            return
        
        from analytics.bot_analytics_postgresql import get_analytics
        analytics = get_analytics()
        
        if analytics and hasattr(analytics, 'Session') and analytics.Session:
            print("✅ Analytics PostgreSQL inicializado")
            return analytics
        else:
            print("❌ Falha ao inicializar Analytics PostgreSQL")
            return None
            
    except Exception as e:
        print(f"❌ Erro na configuração do Analytics: {e}")
        return None

def run_bot_sync():
    """Executa o bot Telegram de forma síncrona (evita problema de signal handlers)"""
    try:
        print("🤖 Iniciando Bot Telegram...")
        
        # Configurar logging
        logging.basicConfig(
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            level=logging.INFO
        )
        
        # Importar e executar o bot diretamente
        import bot
        bot.main()
        
    except Exception as e:
        print(f"❌ Erro no Bot Telegram: {e}")
        traceback.print_exc()

def start_bot_thread():
    """Inicia o bot em uma thread separada (sem asyncio para evitar problemas de signal)"""
    def run_bot():
        try:
            # Executar bot diretamente sem asyncio na thread
            run_bot_sync()
        except Exception as e:
            print(f"❌ Erro na thread do bot: {e}")
            traceback.print_exc()
    
    # Criar e iniciar thread
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    print("✅ Bot Telegram iniciado em thread separada")

def create_app():
    """Cria e configura a aplicação Flask"""
    try:
        from analytics.dashboard_app_render_fixed import app
        print("✅ Aplicação Flask carregada")
        return app
    except Exception as e:
        print(f"❌ Erro ao carregar aplicação Flask: {e}")
        traceback.print_exc()
        return None

def main():
    """Função principal - configura tudo e inicia os serviços"""
    try:
        print("🚀 Iniciando configuração do ambiente...")
        
        # Configurar credenciais e analytics
        setup_credentials()
        setup_analytics()
        
        # Iniciar bot em thread separada
        start_bot_thread()
        
        # Carregar aplicação Flask
        app = create_app()
        if not app:
            print("❌ Falha crítica: não foi possível carregar a aplicação Flask")
            return
        
        # Configurar servidor
        port = int(os.environ.get('PORT', 10000))
        host = '0.0.0.0'
        
        print(f"🌐 Servidor Flask iniciando em {host}:{port}")
        print("🤖 Bot Telegram rodando em paralelo")
        print("🚀 Sistema totalmente operacional!")
        
        # Iniciar servidor Flask
        app.run(host=host, port=port, debug=False, threaded=True)
        
    except Exception as e:
        print(f"❌ Erro crítico na inicialização: {e}")
        traceback.print_exc()

# Executar configurações iniciais
print("⚡ Executando pré-configuração...")
setup_credentials()
setup_analytics()

# Carregar aplicação Flask para Gunicorn
try:
    from analytics.dashboard_app_render_fixed import app
    print("✅ Aplicação Flask pronta para Gunicorn")
except Exception as e:
    print(f"❌ Erro ao carregar Flask para Gunicorn: {e}")
    app = None

if __name__ == '__main__':
    main()
