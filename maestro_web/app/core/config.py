# Arquivo: config.py

import os
from dotenv import load_dotenv
import logging

# --- NOVA SEÇÃO DE CARREGAMENTO (MAIS ROBUSTA) ---

# Configuração do logging para ver as mensagens
logging.basicConfig(level=logging.INFO)

# Pega o caminho absoluto para o diretório onde este arquivo (config.py) está
basedir = os.path.abspath(os.path.dirname(__file__))

# Constrói o caminho para a raiz do projeto (subindo dois níveis de app/core/)
project_root = os.path.dirname(os.path.dirname(basedir))
dotenv_path = os.path.join(project_root, '.env')

# Tenta carregar o arquivo .env com encoding explícito
try:
    if os.path.exists(dotenv_path):
        logging.info(f"Encontrado arquivo .env em: {dotenv_path}")
        # A MÁGICA ESTÁ AQUI: Forçamos a leitura como UTF-8
        load_dotenv(dotenv_path=dotenv_path, encoding='utf-8')
        logging.info("Variáveis de ambiente carregadas com sucesso.")
    else:
        logging.warning(f"AVISO: Arquivo .env não encontrado em {dotenv_path}. Dependendo de variáveis do sistema.")
except Exception as e:
    logging.error(f"Erro CRÍTICO ao carregar o arquivo .env: {e}", exc_info=True)
    # Se não conseguir carregar, o programa continua, mas provavelmente falhará depois.

# --- FIM DA NOVA SEÇÃO DE CARREGAMENTO ---


# --- CARREGAMENTO DAS VARIÁVEIS DE AMBIENTE (sem alteração) ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SECRET_KEY = os.getenv("SECRET_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")
DATABASE_URL = os.getenv("DATABASE_URL")
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")
PIX_KEY = os.getenv("PIX_KEY")


# --- VALIDAÇÃO E CONFIGURAÇÃO ADICIONAL (sem alteração) ---
required_vars = {
    "GEMINI_API_KEY": GEMINI_API_KEY,
    "SECRET_KEY": SECRET_KEY,
    "DATABASE_URL": DATABASE_URL,
    "GOOGLE_APPLICATION_CREDENTIALS": GOOGLE_APPLICATION_CREDENTIALS,
}

missing_vars = [key for key, value in required_vars.items() if not value]
if missing_vars:
    # Removendo o TELEGRAM_TOKEN da validação para a API web
    if "TELEGRAM_TOKEN" in missing_vars:
        missing_vars.remove("TELEGRAM_TOKEN")
    
    if missing_vars:
        raise ValueError(f"As seguintes variáveis de ambiente essenciais não foram definidas no arquivo .env ou no sistema: {', '.join(missing_vars)}")

if GOOGLE_APPLICATION_CREDENTIALS:
    if not os.path.exists(GOOGLE_APPLICATION_CREDENTIALS):
        logging.warning(f"AVISO: O arquivo de credenciais do Google não foi encontrado no caminho especificado: {GOOGLE_APPLICATION_CREDENTIALS}")

# --- CONFIGURAÇÃO ADICIONAL PARA DESENVOLVIMENTO ---
# Definir valores padrão para desenvolvimento
if not SECRET_KEY:
    SECRET_KEY = "sua-chave-secreta-desenvolvimento-muito-longa-e-segura-aqui"
    logging.warning("SECRET_KEY não definida, usando valor padrão para desenvolvimento")

if not DATABASE_URL:
    DATABASE_URL = "sqlite:///./maestro_financeiro.db"
    logging.warning("DATABASE_URL não definida, usando SQLite local")

# Configurações para JWT
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30