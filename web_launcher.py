#!/usr/bin/env python3
"""
🌐 MAESTROFIN WEB LAUNCHER (GUNICORN)
Este script é o ponto de entrada para o servidor web (Gunicorn).
Ele configura o ambiente e expõe a aplicação Flask.
NÃO INICIA O BOT. O bot deve rodar em um Worker Service separado.
"""

import os
import json
import logging

print("\n" + "="*60)
print("╭────────────────────────────────────────────────────────╮")
print("│              🎼 MAESTROFIN DASHBOARD 🎼                │")
print("│         🚀 Gunicorn Web Service Launcher              │")
print("╰────────────────────────────────────────────────────────╯")
print("="*60)

def setup_credentials():
    """Configura credenciais do Google Cloud (Secret Files ou Env Var)"""
    print("🔧 Configurando credenciais Google Cloud para o Web Service...")
    try:
        secret_file = '/etc/secrets/google_vision_credentials.json'
        env_var_json = os.getenv('GOOGLE_VISION_CREDENTIALS_JSON')

        if os.path.exists(secret_file):
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = secret_file
            print("✅ Credenciais configuradas via Secret File.")
        elif env_var_json:
            import tempfile
            creds_data = json.loads(env_var_json)
            # Usar um nome de arquivo fixo no diretório temporário para evitar criar múltiplos arquivos
            temp_file_path = os.path.join(tempfile.gettempdir(), "gcp_creds.json")
            with open(temp_file_path, 'w') as temp_file:
                json.dump(creds_data, temp_file)
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = temp_file_path
            print("✅ Credenciais configuradas via variável de ambiente.")
        else:
            print("⚠️ Nenhuma credencial do Google Cloud configurada para o Web Service.")
    except Exception as e:
        print(f"❌ Erro na configuração de credenciais: {e}")

def setup_analytics():
    """Configura sistema de analytics PostgreSQL para o Web Service"""
    print("🔧 Configurando Analytics PostgreSQL para o Web Service...")
    try:
        if not os.getenv('DATABASE_URL'):
            print("⚠️ DATABASE_URL não configurado - pulando analytics.")
            return

        # Apenas importar para garantir que a conexão funciona
        from analytics.bot_analytics_postgresql import get_analytics
        analytics = get_analytics()
        if analytics:
            print("✅ Conexão com Analytics PostgreSQL verificada.")
        else:
            print("❌ Falha ao verificar Analytics PostgreSQL.")
    except ImportError as e:
        print(f"❌ Erro na importação do Analytics: {e}")
    except Exception as e:
        print(f"❌ Erro na configuração do Analytics: {e}")

# --- Ponto de Entrada para Gunicorn ---

print("⚡ Executando pré-configuração do ambiente web...")
setup_credentials()
setup_analytics()

try:
    # A variável 'app' precisa estar no escopo global para o Gunicorn encontrá-la.
    # O nome do arquivo é 'web_launcher' e o Gunicorn vai procurar por 'web_launcher:app'.
    from analytics.dashboard_app_render_fixed import app
    print("✅ Aplicação Flask carregada e pronta para Gunicorn.")
except ImportError as e:
    print(f"❌ Erro CRÍTICO ao carregar aplicação Flask: {e}")
    logging.critical(f"Não foi possível importar 'app' de 'dashboard_app_render_fixed': {e}")
    # Cria um app dummy para evitar que o Gunicorn falhe completamente no deploy
    from flask import Flask
    app = Flask("error_app")
    @app.route("/")
    def error_page():
        return "<h1>Erro na Aplicação</h1><p>Não foi possível carregar o dashboard. Verifique os logs.</p>", 500