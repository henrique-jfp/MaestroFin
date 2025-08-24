#!/usr/bin/env python3
"""
🌐 MAESTROFIN WEB LAUNCHER - APENAS FLASK
Launcher específico para o serviço web (sem bot integrado)
"""

import os
import json
import logging

def setup_credentials():
    """Configura credenciais do Google Cloud"""
    try:
        secret_file = '/etc/secrets/google_vision_credentials.json'
        env_var_json = os.getenv('GOOGLE_VISION_CREDENTIALS_JSON')
        
        if os.path.exists(secret_file):
            with open(secret_file, 'r') as f:
                secret_data = json.load(f)
            project_id = secret_data.get('project_id', 'N/A')
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = secret_file
            print(f"✅ Google Cloud configurado - Projeto: {project_id}")
        elif env_var_json:
            import tempfile
            creds_data = json.loads(env_var_json)
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
            json.dump(creds_data, temp_file)
            temp_file.close()
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = temp_file.name
            print("✅ Credenciais Google configuradas")
        else:
            print("⚠️ Credenciais Google não encontradas")
    except Exception as e:
        print(f"❌ Erro nas credenciais: {e}")

def setup_analytics():
    """Configura Analytics PostgreSQL"""
    try:
        if not os.getenv('DATABASE_URL'):
            print("⚠️ DATABASE_URL não configurado")
            return
        
        from analytics.bot_analytics_postgresql import get_analytics
        analytics = get_analytics()
        
        if analytics and hasattr(analytics, 'Session') and analytics.Session:
            print("✅ Analytics PostgreSQL configurado")
        else:
            print("❌ Falha no Analytics PostgreSQL")
    except Exception as e:
        print(f"❌ Erro no Analytics: {e}")

# Executar configurações
print("🚀 MAESTROFIN WEB LAUNCHER - Configurando ambiente...")
setup_credentials()
setup_analytics()

# Importar aplicação Flask
try:
    from analytics.dashboard_app_render_fixed import app
    print("✅ Dashboard Flask carregado para Gunicorn")
except Exception as e:
    print(f"❌ Erro ao carregar Dashboard: {e}")
    # Criar app mínima para evitar erro
    from flask import Flask
    app = Flask(__name__)
    
    @app.route('/')
    def health():
        return "MaestroFin Dashboard - Erro na inicialização"

# Configurar logging para produção
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

if __name__ == '__main__':
    # Modo desenvolvimento
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
