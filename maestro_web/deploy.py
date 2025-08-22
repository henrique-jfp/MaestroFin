# deploy.py
"""
Script para facilitar o deploy e configuração de ambiente
"""
import os
import subprocess
import shutil
from pathlib import Path

class DeployManager:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.env_templates = {
            'development': {
                'DATABASE_URL': 'sqlite:///./maestro_financeiro.db',
                'DEBUG': 'True',
                'ENV': 'development'
            },
            'production': {
                'DATABASE_URL': 'postgresql://usuario:senha@host:5432/banco',
                'DEBUG': 'False', 
                'ENV': 'production'
            }
        }
    
    def create_env_file(self, environment='development'):
        """Cria arquivo .env baseado no ambiente"""
        template = self.env_templates.get(environment, self.env_templates['development'])
        
        env_content = f"""# Ambiente: {environment}
# Gerado automaticamente em {os.popen('date').read().strip()}

# Database
DATABASE_URL={template['DATABASE_URL']}

# JWT
SECRET_KEY=sua-chave-secreta-muito-segura-aqui-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# IA
GEMINI_API_KEY=sua-chave-gemini-aqui

# Configurações gerais
DEBUG={template['DEBUG']}
ENV={template['ENV']}

# Email (opcional)
SENDER_EMAIL=seu-email@gmail.com
EMAIL_HOST_USER=seu-usuario-smtp
EMAIL_HOST_PASSWORD=sua-senha-smtp
EMAIL_RECEIVER=destinatario@gmail.com

# PIX (opcional)
PIX_KEY=sua-chave-pix-aqui
"""
        
        env_file = self.project_root / '.env'
        with open(env_file, 'w') as f:
            f.write(env_content)
        
        print(f"✅ Arquivo .env criado para {environment}")
        print(f"📝 Edite o arquivo .env com suas configurações reais")
    
    def install_dependencies(self):
        """Instala dependências necessárias"""
        print("📦 Instalando dependências...")
        
        # Dependências básicas
        basic_deps = [
            "fastapi",
            "uvicorn[standard]",
            "sqlalchemy",
            "python-dotenv",
            "python-multipart",
            "python-jose[cryptography]",
            "passlib[bcrypt]",
            "psycopg2-binary"  # Para PostgreSQL
        ]
        
        for dep in basic_deps:
            try:
                subprocess.run(['pip', 'install', dep], check=True)
                print(f"✅ {dep} instalado")
            except subprocess.CalledProcessError:
                print(f"❌ Erro ao instalar {dep}")
    
    def setup_frontend(self):
        """Configura o frontend Next.js"""
        frontend_path = self.project_root / 'maestrofin-web'
        
        if not frontend_path.exists():
            print("❌ Diretório do frontend não encontrado")
            return
        
        print("🎨 Configurando frontend...")
        
        # Instalar dependências do Node.js
        try:
            subprocess.run(['npm', 'install'], cwd=frontend_path, check=True)
            print("✅ Dependências do frontend instaladas")
        except subprocess.CalledProcessError:
            print("❌ Erro ao instalar dependências do frontend")
    
    def run_development(self):
        """Inicia servidores de desenvolvimento"""
        print("🚀 Iniciando desenvolvimento...")
        
        # Backend
        backend_cmd = "python -m uvicorn app.main:app --reload --port 8000"
        print(f"Backend: {backend_cmd}")
        
        # Frontend
        frontend_path = self.project_root / 'maestrofin-web'
        frontend_cmd = f"cd {frontend_path} && npm run dev"
        print(f"Frontend: {frontend_cmd}")
        
        print("\n📋 Comandos para executar em terminais separados:")
        print(f"Terminal 1: {backend_cmd}")
        print(f"Terminal 2: {frontend_cmd}")
    
    def production_checklist(self):
        """Lista verificações para produção"""
        print("\n🔍 Checklist para Produção:")
        print("=" * 40)
        
        checklist = [
            "✓ Configurar DATABASE_URL com PostgreSQL",
            "✓ Definir SECRET_KEY segura",
            "✓ Configurar GEMINI_API_KEY",
            "✓ Configurar domínio e SSL",
            "✓ Configurar CORS no backend",
            "✓ Fazer backup do SQLite local",
            "✓ Executar migrate.py",
            "✓ Testar todas as funcionalidades",
            "✓ Configurar monitoramento de logs"
        ]
        
        for item in checklist:
            print(f"  {item}")
        
        print("\n🔗 Plataformas recomendadas:")
        print("Backend: Railway, Render, Heroku")
        print("Frontend: Vercel, Netlify")
        print("Banco: Supabase, PlanetScale, Railway")

def main():
    """Menu principal"""
    manager = DeployManager()
    
    print("🎼 Maestro Financeiro - Deploy Manager")
    print("=" * 50)
    
    while True:
        print("\nOpções:")
        print("1. Criar .env para desenvolvimento")
        print("2. Criar .env para produção")
        print("3. Instalar dependências")
        print("4. Configurar frontend")
        print("5. Executar desenvolvimento")
        print("6. Checklist de produção")
        print("0. Sair")
        
        choice = input("\nEscolha uma opção: ")
        
        if choice == '1':
            manager.create_env_file('development')
        elif choice == '2':
            manager.create_env_file('production')
        elif choice == '3':
            manager.install_dependencies()
        elif choice == '4':
            manager.setup_frontend()
        elif choice == '5':
            manager.run_development()
        elif choice == '6':
            manager.production_checklist()
        elif choice == '0':
            print("👋 Até logo!")
            break
        else:
            print("❌ Opção inválida")

if __name__ == "__main__":
    main()
