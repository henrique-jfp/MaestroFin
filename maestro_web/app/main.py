import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from dotenv import load_dotenv

# 1. Importe tudo que você precisa primeiro
from .core.database import criar_tabelas, popular_dados_iniciais, get_db
from .api import auth, metas
from .api import auth, metas, lancamentos
from .api import contas
from .api import categorias
from .api import agendamentos
from .api import relatorios, graficos
from .api import chat
from .api import dashboard
from .api import ocr
# 2. Configure o logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 3. Crie a instância principal do FastAPI
#    É crucial que esta linha venha ANTES de você usar a variável 'app'
app = FastAPI(
    title="Maestro Financeiro API",
    description="API para o seu assistente pessoal de finanças.",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# 4. Execute a lógica de inicialização (como criar tabelas)
#    Isso pode ser feito aqui ou usando eventos de startup do FastAPI
try:
    logger.info("Inicializando a aplicação e o banco de dados...")
    criar_tabelas()
    db: Session = next(get_db())
    popular_dados_iniciais(db)
    db.close()
    logger.info("Banco de dados pronto.")
except Exception as e:
    logger.critical(f"Falha crítica na configuração do banco de dados: {e}", exc_info=True)
    # Em um cenário real, você pode querer que a aplicação não inicie se o DB falhar.

# 5. Inclua os roteadores da sua API
app.include_router(auth.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(metas.router, prefix="/api")
app.include_router(lancamentos.router, prefix="/api") 
app.include_router(contas.router, prefix="/api")
app.include_router(categorias.router, prefix="/api")
app.include_router(agendamentos.router, prefix="/api")
app.include_router(relatorios.router, prefix="/api")
app.include_router(graficos.router, prefix="/api")
app.include_router(ocr.router, prefix="/api")
# 6. Defina as rotas da raiz (se houver)
@app.get("/", tags=["Root"])
async def read_root():
    """Verifica se a API está online."""
    return {"message": "Bem-vindo à API do Maestro Financeiro! 🎼"}