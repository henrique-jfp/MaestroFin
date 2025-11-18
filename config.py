# Arquivo: config.py

import os
import logging

# Configurar logging básico
logging.basicConfig(level=logging.INFO)

# --- CARREGAMENTO DO .ENV APENAS EM DESENVOLVIMENTO ---

# Verificar se estamos em ambiente de produção (Railway)
is_production = bool(os.getenv('RAILWAY_ENVIRONMENT') or os.getenv('PORT'))

if not is_production:
    # Apenas em desenvolvimento, tenta carregar .env
    try:
        from dotenv import load_dotenv
        
        # Pega o caminho absoluto para o diretório onde este arquivo está
        basedir = os.path.abspath(os.path.dirname(__file__))
        dotenv_path = os.path.join(basedir, '.env')
        
        # Verifica se o arquivo .env existe
        if os.path.exists(dotenv_path):
            logging.info(f"🔧 [DEV] Carregando variáveis de ambiente de: {dotenv_path}")
            load_dotenv(dotenv_path=dotenv_path)
        else:
            logging.info("🔧 [DEV] Arquivo .env não encontrado, usando variáveis de ambiente do sistema")
    except ImportError:
        logging.info("🔧 [DEV] python-dotenv não instalado, usando variáveis de ambiente do sistema")
else:
    logging.info("🌐 [PROD] Ambiente de produção detectado - usando variáveis de ambiente do sistema")


# --- CARREGAMENTO DAS VARIÁVEIS DE AMBIENTE ---

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-1.5-flash")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")
DATABASE_URL = os.getenv("DATABASE_URL")
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

# ----- ADICIONANDO VARIÁVEL DE CHAVE PIX E CONTATO -----
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")
PIX_KEY = os.getenv("PIX_KEY")

# ----- PLUGGY / OPEN FINANCE -----
PLUGGY_CLIENT_ID = os.getenv("PLUGGY_CLIENT_ID")
PLUGGY_CLIENT_SECRET = os.getenv("PLUGGY_CLIENT_SECRET")


# --- VALIDAÇÃO E CONFIGURAÇÃO ADICIONAL ---

# Verificar apenas variáveis críticas para o bot funcionar
if not TELEGRAM_TOKEN:
    if is_production:
        logging.warning("⚠️ TELEGRAM_TOKEN não configurado no Render - Dashboard funcionará apenas com dados mock")
        # Em produção sem token, não quebra, mas avisa
        TELEGRAM_TOKEN = None
    else:
        logging.error("❌ TELEGRAM_TOKEN não configurado!")
        raise ValueError("TELEGRAM_TOKEN é obrigatório para o bot funcionar")

# Verificar outras variáveis importantes
missing_vars = []
if not GEMINI_API_KEY:
    missing_vars.append("GEMINI_API_KEY")
if not PIX_KEY:
    missing_vars.append("PIX_KEY")
if not EMAIL_HOST_PASSWORD:
    missing_vars.append("EMAIL_HOST_PASSWORD")

if missing_vars:
    logging.warning(f"⚠️ Variáveis não configuradas: {', '.join(missing_vars)}")
    if is_production:
        logging.info("📊 Dashboard funcionará com dados mock até variáveis serem configuradas")

# Log das configurações (sem expor tokens)
logging.info("✅ Configurações carregadas:")
logging.info(f"   📱 TELEGRAM_TOKEN: {'✅ Configurado' if TELEGRAM_TOKEN else '❌ Não encontrado'}")
logging.info(f"   🤖 GEMINI_API_KEY: {'✅ Configurado' if GEMINI_API_KEY else '⚠️ Não encontrado'}")
logging.info(f"   🗄️ DATABASE_URL: {'✅ Configurado' if DATABASE_URL else '⚠️ Não encontrado'}")

# Log das configurações de email e PIX (para debug)
logging.info(f"   📧 EMAIL_HOST_USER: {'✅ Configurado' if EMAIL_HOST_USER else '❌ Não encontrado'}")
logging.info(f"   📧 EMAIL_HOST_PASSWORD: {'✅ Configurado' if EMAIL_HOST_PASSWORD else '❌ Não encontrado'}")
logging.info(f"   📧 SENDER_EMAIL: {'✅ Configurado' if SENDER_EMAIL else '❌ Não encontrado'}")
logging.info(f"   📧 EMAIL_RECEIVER: {'✅ Configurado' if EMAIL_RECEIVER else '❌ Não encontrado'}")
logging.info(f"   💳 PIX_KEY: {'✅ Configurado' if PIX_KEY else '❌ Não encontrado'}")

# Log de Pluggy / Open Finance
logging.info(f"   🔌 PLUGGY_CLIENT_ID: {'✅ Configurado' if PLUGGY_CLIENT_ID else '❌ Não encontrado'}")
logging.info(f"   🔌 PLUGGY_CLIENT_SECRET: {'✅ Configurado' if PLUGGY_CLIENT_SECRET else '❌ Não encontrado'}")

# Configurar credenciais do Google de forma mais flexível
if GOOGLE_APPLICATION_CREDENTIALS:
    basedir = os.path.abspath(os.path.dirname(__file__))
    if not os.path.isabs(GOOGLE_APPLICATION_CREDENTIALS):
        google_creds_path = os.path.join(basedir, GOOGLE_APPLICATION_CREDENTIALS)
    else:
        google_creds_path = GOOGLE_APPLICATION_CREDENTIALS
    
    if os.path.exists(google_creds_path):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = google_creds_path
        logging.info(f"✅ Google Application Credentials configurado: {google_creds_path}")
    else:
        logging.warning(f"⚠️ Arquivo de credenciais não encontrado: {google_creds_path}")
        logging.info("⚠️ Funcionalidades do Google Vision podem não funcionar")
else:
    logging.info("ℹ️ GOOGLE_APPLICATION_CREDENTIALS não configurado - funcionalidades OCR limitadas")