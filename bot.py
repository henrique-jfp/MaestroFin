import logging
import warnings
import google.generativeai as genai
import os
import functools
from datetime import time
from telegram.warnings import PTBUserWarning
import threading
from flask import Flask, jsonify

# 🔐 CARREGAR SECRET FILES PRIMEIRO
try:
    from secret_loader import setup_environment
    setup_environment()
    logging.info("✅ Secret Files carregado com sucesso")
except ImportError:
    logging.warning("⚠️ secret_loader não encontrado")
except Exception as e:
    logging.error(f"❌ Erro ao carregar Secret Files: {e}")

# Suprimir warnings do python-telegram-bot
warnings.filterwarnings("ignore", category=PTBUserWarning, module="telegram")

# 🚀 INICIALIZAR OCR
try:
    from gerente_financeiro.ocr_handler import setup_google_credentials
    setup_success = setup_google_credentials()
    if setup_success:
        logging.info("✅ OCR: Credenciais Google Vision configuradas")
    else:
        logging.warning("⚠️ OCR: Usando apenas fallback Gemini")
except Exception as ocr_init_error:
    logging.error(f"❌ OCR: Erro na inicialização - {ocr_init_error}")

# Inicializar Analytics
try:
    if os.getenv('DATABASE_URL'):  # Render
        from analytics.bot_analytics_postgresql import get_analytics, track_command
        analytics = get_analytics()
        logging.info("✅ Analytics PostgreSQL integrado (RENDER)")
    else:  # Local
        from analytics.bot_analytics import BotAnalytics, track_command
        analytics = BotAnalytics()
        logging.info("✅ Analytics SQLite integrado (LOCAL)")
    
    ANALYTICS_ENABLED = True
except ImportError as e:
    ANALYTICS_ENABLED = False
    logging.warning(f"⚠️ Analytics não disponível: {e}")

def track_analytics(command_name):
    """Decorator para tracking de comandos"""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(update, context):
            if ANALYTICS_ENABLED and update.effective_user:
                user_id = update.effective_user.id
                username = update.effective_user.username or update.effective_user.first_name or "Usuário"
                
                try:
                    analytics.track_command_usage(
                        user_id=user_id,
                        username=username,
                        command=command_name,
                        success=True
                    )
                    analytics.track_daily_user(user_id, username, command_name)
                    logging.info(f"📊 Analytics: {username} usou /{command_name}")
                except Exception as e:
                    logging.error(f"❌ Erro no analytics: {e}")
            
            return await func(update, context)
        return wrapper
    return decorator

# Health check server
health_app = Flask(__name__)

@health_app.route('/health')
def health_check():
    return jsonify({"status": "healthy", "service": "MaestroFin Bot"})

@health_app.route('/')
def home():
    return jsonify({
        "service": "MaestroFin Bot",
        "status": "running",
        "version": "3.1.0"
    })

from gerente_financeiro.extrato_handler import criar_conversation_handler_extrato
from sqlalchemy.orm import Session, joinedload
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    CallbackQueryHandler, ConversationHandler, ApplicationBuilder, ContextTypes
)

# --- IMPORTS DO PROJETO ---
import config
from database.database import get_db, popular_dados_iniciais, criar_tabelas
from models import *
from alerts import schedule_alerts
from jobs import configurar_jobs

# --- IMPORTS DOS HANDLERS (AGORA ORGANIZADOS) ---
from gerente_financeiro.handlers import (
    create_gerente_conversation_handler, 
    create_cadastro_email_conversation_handler,
    handle_analise_impacto_callback,  
    help_callback, 
    help_command,
    cancel,
    painel_notificacoes
)
from gerente_financeiro.agendamentos_handler import (
    agendamento_start, agendamento_conv, agendamento_menu_callback, cancelar_agendamento_callback
)
from gerente_financeiro.metas_handler import (
    objetivo_conv, listar_metas_command, deletar_meta_callback, edit_meta_conv
)
from gerente_financeiro.onboarding_handler import configurar_conv
from gerente_financeiro.editing_handler import edit_conv
from gerente_financeiro.graficos import grafico_conv
from gerente_financeiro.relatorio_handler import relatorio_handler
from gerente_financeiro.manual_entry_handler import manual_entry_conv
from gerente_financeiro.contact_handler import contact_conv
from gerente_financeiro.delete_user_handler import delete_user_conv
from gerente_financeiro.fatura_handler import (
    fatura_conv, callback_agendar_parcelas_sim, callback_agendar_parcelas_nao
)  # <-- Importar também os callbacks
from gerente_financeiro.dashboard_handler import (
    cmd_dashboard, cmd_dashstatus, dashboard_callback_handler
)
from gerente_financeiro.gamification_handler import show_profile, show_rankings, handle_gamification_callback

# 🔧 HANDLER GENÉRICO DE DOCUMENTOS
from document_handler_addon import create_document_handlers

# --- COMANDOS DE DEBUG (REMOVER EM PRODUÇÃO) ---
@track_analytics("dashboarddebug")
async def debug_dashboard(update, context):
    """Comando de debug do dashboard"""
    try:
        user_id = update.effective_user.id
        
        # Testar dashboard
        import requests
        try:
            response = requests.get("http://localhost:5001/api/status", timeout=3)
            if response.status_code == 200:
                dashboard_status = "✅ Online"
                data = response.json()
                status_info = f"Status: {data.get('status', 'unknown')}"
            else:
                dashboard_status = "❌ Erro HTTP"
                status_info = f"Código: {response.status_code}"
        except Exception as e:
            dashboard_status = "❌ Offline"
            status_info = f"Erro: {str(e)[:50]}"
        
        message = f"""🔍 **DEBUG DASHBOARD**

📊 **Dashboard**: {dashboard_status}
{status_info}

👤 **User ID**: {user_id}

🌐 **URLs**:
• Dashboard: http://localhost:5000
• Demo: http://localhost:5000/dashboard/demo"""

        await update.message.reply_text(message, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(f"🚨 **ERRO DEBUG**: {str(e)}")

# --- CONFIGURAÇÃO INICIAL ---
warnings.filterwarnings("ignore", category=PTBUserWarning)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# --- FUNÇÕES PRINCIPAIS DO BOT ---

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Loga os erros e envia uma mensagem de erro genérica."""
    import traceback
    
    # Log detalhado do erro
    print(f"\n🚨 ERRO GLOBAL CAPTURADO:")
    print(f"Tipo: {type(context.error).__name__}")
    print(f"Mensagem: {str(context.error)}")
    print(f"Traceback:")
    print(traceback.format_exc())
    
    logger.error("Exception while handling an update:", exc_info=context.error)
    
    if hasattr(update, 'effective_message') and update.effective_message:
        try:
            await update.effective_message.reply_text("⚠️ Ocorreu um erro inesperado. Minha equipe já foi notificada.")
        except Exception as e:
            logger.error(f"Failed to send error message to user: {e}")
            print(f"❌ Erro ao enviar mensagem de erro: {e}")

def main() -> None:
    """Função principal que monta e executa o bot."""
    logger.info("Iniciando o bot...")

    # Configuração do Banco de Dados
    try:
        criar_tabelas()
        db: Session = next(get_db())
        popular_dados_iniciais(db)
        db.close()
        logger.info("Banco de dados pronto.")
    except Exception as e:
        logger.critical(f"Falha crítica na configuração do banco de dados: {e}", exc_info=True)
        return

    # Configuração da API do Gemini
    try:
        genai.configure(api_key=config.GEMINI_API_KEY)
        logger.info("API do Gemini configurada.")
    except Exception as e:
        logger.critical(f"Falha ao configurar a API do Gemini: {e}")
        return

    # Construção da Aplicação do Bot
    application = ApplicationBuilder().token(config.TELEGRAM_TOKEN).build()
    logger.info("Aplicação do bot criada.")

    
    gerente_conv = create_gerente_conversation_handler()
    email_conv = create_cadastro_email_conversation_handler()
    
    # Adicionando todos os handlers à aplicação
    logger.info("Adicionando handlers...")
    
    # Handlers de Conversa (ConversationHandler)
    application.add_handler(configurar_conv)  # Inclui o /start agora
    application.add_handler(gerente_conv)
    application.add_handler(email_conv)
    application.add_handler(manual_entry_conv)
    application.add_handler(fatura_conv)        # Adicionado aqui
    application.add_handler(delete_user_conv)
    application.add_handler(contact_conv)
    application.add_handler(grafico_conv)
    application.add_handler(objetivo_conv)
    application.add_handler(edit_meta_conv)
    application.add_handler(agendamento_conv)
    application.add_handler(edit_conv)
    application.add_handler(criar_conversation_handler_extrato())
    
    # Handlers de Comando (CommandHandler)
    application.add_handler(relatorio_handler)  # É um CommandHandler, não uma conversa
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("alerta", schedule_alerts))
    application.add_handler(CommandHandler("metas", listar_metas_command))
    application.add_handler(CommandHandler("agendar", agendamento_start))
    application.add_handler(CommandHandler("notificacoes", painel_notificacoes))
    
    # � GAMIFICATION HANDLERS
    application.add_handler(CommandHandler("perfil", show_profile))
    application.add_handler(CommandHandler("ranking", show_rankings))
    
    # �🌐 DASHBOARD HANDLERS
    application.add_handler(CommandHandler("dashboard", cmd_dashboard))  # DASHBOARD PRINCIPAL
    application.add_handler(CommandHandler("dashstatus", cmd_dashstatus))
    application.add_handler(CommandHandler("dashboarddebug", debug_dashboard))  # DEBUG
    
    # Handlers de Callback (CallbackQueryHandler) para menus e botões
    application.add_handler(CallbackQueryHandler(help_callback, pattern="^help_"))
    application.add_handler(CallbackQueryHandler(handle_analise_impacto_callback, pattern="^analise_"))
    application.add_handler(CallbackQueryHandler(deletar_meta_callback, pattern="^deletar_meta_"))
    application.add_handler(CallbackQueryHandler(agendamento_menu_callback, pattern="^agendamento_"))
    application.add_handler(CallbackQueryHandler(cancelar_agendamento_callback, pattern="^ag_cancelar_"))
    
    # � GAMIFICATION CALLBACKS
    application.add_handler(CallbackQueryHandler(handle_gamification_callback, pattern="^(show_rankings|show_stats|show_rewards)$"))
    
    # �🌐 DASHBOARD CALLBACKS
    application.add_handler(CallbackQueryHandler(dashboard_callback_handler, pattern="^dashboard_"))
    
    # 🆕 NOVOS: Handlers independentes para callbacks de agendamento de parcelas
    application.add_handler(CallbackQueryHandler(callback_agendar_parcelas_sim, pattern="^fatura_agendar_sim$"))
    application.add_handler(CallbackQueryHandler(callback_agendar_parcelas_nao, pattern="^fatura_agendar_nao$"))
    
    # 🔧 HANDLER GENÉRICO DE DOCUMENTOS/FOTOS
    document_handlers = create_document_handlers()
    for handler in document_handlers:
        application.add_handler(handler)
    logger.info("✅ Handlers genéricos de documentos adicionados")
    
    # Handler de Erro
    application.add_error_handler(error_handler)
    logger.info("Todos os handlers adicionados com sucesso.")
    
    # Configuração e inicialização dos Jobs agendados
    job_queue = application.job_queue
    configurar_jobs(job_queue)
    logger.info("Jobs de metas e agendamentos configurados.")
    
    # Inicia o bot
    logger.info("Bot pronto. Iniciando polling...")
    application.run_polling()
    logger.info("Bot foi encerrado.")

if __name__ == '__main__':
    main()