import logging
import warnings
import google.generativeai as genai
import os
import functools
from datetime import time, datetime
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
    """Decorator avançado para tracking de comandos"""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(update, context):
            if ANALYTICS_ENABLED and update.effective_user:
                user_id = update.effective_user.id
                username = update.effective_user.username or update.effective_user.first_name or "Usuário"
                
                start_time = datetime.now()
                success = True
                error_details = None
                
                try:
                    # Executar comando
                    result = await func(update, context)
                    
                    # Calcular tempo de execução
                    execution_time = (datetime.now() - start_time).total_seconds() * 1000
                    
                    # Registrar sucesso
                    analytics.track_command_usage(
                        user_id=user_id,
                        username=username,
                        command=command_name,
                        success=True,
                        execution_time_ms=int(execution_time)
                    )
                    
                    # track_daily_user() removido - método não existe
                    
                    logging.info(f"📊 Analytics: {username} usou /{command_name} ({execution_time:.0f}ms)")
                    return result
                    
                except Exception as e:
                    success = False
                    error_details = str(e)
                    execution_time = (datetime.now() - start_time).total_seconds() * 1000
                    
                    # Registrar falha
                    analytics.track_command_usage(
                        user_id=user_id,
                        username=username,
                        command=command_name,
                        success=False,
                        execution_time_ms=int(execution_time)
                    )
                    
                    # Log detalhado do erro
                    if hasattr(analytics, 'log_error'):
                        import traceback
                        analytics.log_error(
                            error_type=type(e).__name__,
                            error_message=str(e),
                            stack_trace=traceback.format_exc(),
                            user_id=user_id,
                            username=username,
                            command=command_name
                        )
                    
                    logging.error(f"❌ Erro no comando /{command_name}: {e}")
                    raise  # Re-propagar o erro
                    
            else:
                # Executar sem analytics
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
from gerente_financeiro.dashboard_handler import (
    cmd_dashboard, cmd_dashstatus, dashboard_callback_handler
)
from gerente_financeiro.gamification_handler import show_profile, show_rankings, handle_gamification_callback

# 📈 INVESTMENT HANDLER
from gerente_financeiro.investment_handler import get_investment_handlers

# 🏦 OPEN FINANCE OAUTH (substitui handler antigo)
try:
    from gerente_financeiro.open_finance_oauth_handler import OpenFinanceOAuthHandler
    from open_finance.data_sync import schedule_daily_sync
    OPEN_FINANCE_OAUTH_ENABLED = True
    logging.info("✅ Open Finance OAuth habilitado")
except Exception as e:
    OPEN_FINANCE_OAUTH_ENABLED = False
    logging.error(f"❌ Open Finance OAuth não disponível: {e}", exc_info=True)

# --- COMANDOS DE DEBUG (REMOVER EM PRODUÇÃO) ---
@track_analytics("debugocr")
async def debug_ocr_command(update, context):
    """Comando específico para debug do OCR /lancamento"""
    try:
        user_id = update.effective_user.id
        
        message = f"""🔍 **DEBUG OCR LANCAMENTO**

👤 **User ID**: {user_id}

🌍 **Environment Check**:
• GEMINI_API_KEY: {'✅ SET' if os.getenv('GEMINI_API_KEY') else '❌ NOT SET'}
• GOOGLE_VISION: {'✅ SET' if os.getenv('GOOGLE_APPLICATION_CREDENTIALS') or os.getenv('GOOGLE_VISION_CREDENTIALS_JSON') else '❌ NOT SET'}
• RENDER: {'✅ YES' if os.getenv('RENDER') else '❌ NO (LOCAL)'}

📦 **Module Check**:"""

        # Testar importações
        try:
            import google.generativeai as genai
            message += "\n• Gemini: ✅ OK"
        except Exception as e:
            message += f"\n• Gemini: ❌ {str(e)[:30]}"
        
        try:
            from google.cloud import vision
            message += "\n• Google Vision: ✅ OK"
        except Exception as e:
            message += f"\n• Google Vision: ❌ {str(e)[:30]}"
        
        try:
            from PIL import Image
            message += "\n• PIL: ✅ OK"
        except Exception as e:
            message += f"\n• PIL: ❌ {str(e)[:30]}"

        message += f"""

🔬 **Credential Files**:"""
        
        # Verificar arquivos de credenciais
        cred_files = [
            'credenciais/credentials.json',
            'credenciais/googlevision2.json'
        ]
        
        for cred_file in cred_files:
            if os.path.exists(cred_file):
                size = os.path.getsize(cred_file)
                message += f"\n• {cred_file}: ✅ ({size} bytes)"
            else:
                message += f"\n• {cred_file}: ❌ NOT FOUND"

        message += f"""

📱 **Como testar**:
1. Envie /lancamento
2. Envie uma foto de nota fiscal
3. Se der erro, envie o print do erro
4. Execute /debuglogs para ver logs detalhados

🎯 **Status**: Sistema de debug ativo"""

        await update.message.reply_text(message, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(f"🚨 **ERRO DEBUG OCR**: {str(e)}")

@track_analytics("debuglogs")
async def debug_logs_command(update, context):
    """Mostrar logs recentes de erro do OCR"""
    try:
        import glob
        
        # Procurar arquivos de log recentes
        log_files = glob.glob('debug_logs/ocr_debug_*.log')
        if not log_files:
            await update.message.reply_text("📝 Nenhum log de debug encontrado. Execute /debugocr primeiro.")
            return
        
        # Pegar o log mais recente
        latest_log = max(log_files, key=os.path.getctime)
        
        try:
            with open(latest_log, 'r', encoding='utf-8') as f:
                log_content = f.read()
            
            # Limitar tamanho da mensagem
            if len(log_content) > 3500:
                log_content = log_content[-3500:]
                log_content = "...\n" + log_content
            
            message = f"📝 **LOG DEBUG OCR**\n```\n{log_content}\n```"
            
        except Exception as e:
            message = f"❌ Erro ao ler log: {str(e)}"
        
        await update.message.reply_text(message, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(f"🚨 **ERRO LOGS**: {str(e)}")

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


def _register_default_handlers(application: Application, safe_mode: bool = False) -> None:
    """Registra em um único ponto os handlers necessários para o bot."""

    def add(handler, name: str) -> None:
        try:
            application.add_handler(handler)
            logger.debug("Handler %s registrado", name)
        except Exception as exc:
            if safe_mode:
                logger.warning("⚠️ Handler %s indisponível: %s", name, exc)
            else:
                raise

    def build_and_add(name: str, builder) -> None:
        try:
            handler = builder()
        except Exception as exc:
            if safe_mode:
                logger.warning("⚠️ Falha ao construir %s: %s", name, exc)
                return
            raise
        add(handler, name)

    logger.info("🔧 Registrando handlers padrão do bot...")

    conversation_builders = [
        ("configurar_conv", lambda: configurar_conv),
        ("gerente_conv", create_gerente_conversation_handler),
        ("cadastro_email_conv", create_cadastro_email_conversation_handler),
        ("manual_entry_conv", lambda: manual_entry_conv),
        ("delete_user_conv", lambda: delete_user_conv),
        ("contact_conv", lambda: contact_conv),
        ("grafico_conv", lambda: grafico_conv),
        ("objetivo_conv", lambda: objetivo_conv),
        ("edit_meta_conv", lambda: edit_meta_conv),
        ("agendamento_conv", lambda: agendamento_conv),
        ("edit_conv", lambda: edit_conv),
    ]
    
    # 🔐 Open Finance OAuth - Substitui handler antigo
    of_oauth_handler = None
    if OPEN_FINANCE_OAUTH_ENABLED:
        try:
            logger.info("🔄 Instanciando OpenFinanceOAuthHandler...")
            of_oauth_handler = OpenFinanceOAuthHandler()
            logger.info("🔄 Criando conversation handler...")
            conversation_builders.append(
                ("open_finance_oauth_conv", lambda: of_oauth_handler.get_conversation_handler())
            )
            logger.info("✅ Open Finance OAuth handler registrado")
        except Exception as e:
            logger.error(f"❌ Erro ao registrar Open Finance OAuth: {e}", exc_info=True)

    for name, builder in conversation_builders:
        build_and_add(name, builder)

    command_builders = [
        ("relatorio_handler", lambda: relatorio_handler),
        ("/help", lambda: CommandHandler("help", help_command)),
        ("/alerta", lambda: CommandHandler("alerta", schedule_alerts)),
        ("/metas", lambda: CommandHandler("metas", listar_metas_command)),
        ("/agendar", lambda: CommandHandler("agendar", agendamento_start)),
        ("/notificacoes", lambda: CommandHandler("notificacoes", painel_notificacoes)),
        ("/perfil", lambda: CommandHandler("perfil", show_profile)),
        ("/ranking", lambda: CommandHandler("ranking", show_rankings)),
        ("/dashboard", lambda: CommandHandler("dashboard", cmd_dashboard)),
        ("/dashstatus", lambda: CommandHandler("dashstatus", cmd_dashstatus)),
        ("/dashboarddebug", lambda: CommandHandler("dashboarddebug", debug_dashboard)),
        ("/debugocr", lambda: CommandHandler("debugocr", debug_ocr_command)),
        ("/debuglogs", lambda: CommandHandler("debuglogs", debug_logs_command)),
    ]
    
    # Adicionar comandos Open Finance se habilitado
    if OPEN_FINANCE_OAUTH_ENABLED and of_oauth_handler:
        command_builders.extend([
            ("/minhas_contas", lambda: CommandHandler("minhas_contas", of_oauth_handler.minhas_contas)),
            ("/sincronizar", lambda: CommandHandler("sincronizar", of_oauth_handler.sincronizar)),
            ("/importar_transacoes", lambda: CommandHandler("importar_transacoes", of_oauth_handler.importar_transacoes)),
            ("/categorizar", lambda: CommandHandler("categorizar", of_oauth_handler.categorizar_lancamentos)),
        ])
        logger.info("✅ Comandos Open Finance adicionados: /minhas_contas, /sincronizar, /importar_transacoes, /categorizar")
    
    # Adicionar handlers de investimentos
    try:
        investment_handlers = get_investment_handlers()
        for handler in investment_handlers:
            application.add_handler(handler)
        logger.info("✅ Handlers de investimentos registrados: /investimentos, /dashboard_investimentos, /patrimonio")
    except Exception as e:
        logger.error(f"❌ Erro ao registrar handlers de investimentos: {e}", exc_info=True)

    for name, builder in command_builders:
        build_and_add(name, builder)

    callback_builders = [
        ("help_callback", lambda: CallbackQueryHandler(help_callback, pattern="^help_")),
        ("analise_callback", lambda: CallbackQueryHandler(handle_analise_impacto_callback, pattern="^analise_")),
        ("deletar_meta_callback", lambda: CallbackQueryHandler(deletar_meta_callback, pattern="^deletar_meta_")),
        ("agendamento_menu_callback", lambda: CallbackQueryHandler(agendamento_menu_callback, pattern="^agendamento_")),
        ("cancelar_agendamento_callback", lambda: CallbackQueryHandler(cancelar_agendamento_callback, pattern="^ag_cancelar_")),
        ("gamificacao_callback", lambda: CallbackQueryHandler(handle_gamification_callback, pattern="^(show_rankings|show_stats|show_rewards)$")),
        ("dashboard_callback", lambda: CallbackQueryHandler(dashboard_callback_handler, pattern="^dashboard_")),
    ]
    
    # Adicionar callback handlers Open Finance
    if OPEN_FINANCE_OAUTH_ENABLED and of_oauth_handler:
        callback_builders.extend([
            ("import_callback", lambda: CallbackQueryHandler(of_oauth_handler.handle_import_callback, pattern="^import_")),
            ("action_callback", lambda: CallbackQueryHandler(of_oauth_handler.handle_action_callback, pattern="^action_")),
            ("of_sync_now", lambda: CallbackQueryHandler(of_oauth_handler.handle_sync_now_callback, pattern="^of_sync_now_")),
            ("of_view_accounts", lambda: CallbackQueryHandler(of_oauth_handler.handle_view_accounts_callback, pattern="^of_view_accounts$"))
        ])
        logger.info("✅ Callback handlers Open Finance adicionados (import, action, sync_now, view_accounts)")

    for name, builder in callback_builders:
        build_and_add(name, builder)

    # ❌ Handler antigo removido - substituído por OpenFinanceOAuthHandler
    # O novo handler OAuth é mais seguro e suporta 100+ bancos

    try:
        from gerente_financeiro.spx_handler import spx_handler
        from gerente_financeiro.spx_metas_handler import spx_metas_handler
        from gerente_financeiro.spx_dashboard import spx_dashboard

        spx_conv = ConversationHandler(
            entry_points=[CommandHandler('spx', spx_handler.comando_spx)],
            states={
                spx_handler.SPX_GANHOS: [MessageHandler(filters.TEXT & ~filters.COMMAND, spx_handler.processar_ganhos)],
                spx_handler.SPX_COMBUSTIVEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, spx_handler.processar_combustivel)],
                spx_handler.SPX_OUTROS_GASTOS: [MessageHandler(filters.TEXT & ~filters.COMMAND, spx_handler.processar_outros_gastos)],
                spx_handler.SPX_QUILOMETRAGEM: [MessageHandler(filters.TEXT & ~filters.COMMAND, spx_handler.processar_quilometragem)],
                spx_handler.SPX_HORAS: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, spx_handler.processar_horas),
                    CallbackQueryHandler(spx_handler.pular_horas, pattern="^spx_pular_horas$")
                ],
                spx_handler.SPX_ENTREGAS: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, spx_handler.processar_entregas),
                    CallbackQueryHandler(spx_handler.finalizar_sem_entregas, pattern="^spx_finalizar_sem_entregas$")
                ],
                spx_handler.SPX_OBSERVACOES: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, spx_handler.processar_observacoes),
                    CallbackQueryHandler(spx_handler.pular_observacoes, pattern="^spx_confirmar_registro$")
                ],
                spx_handler.SPX_CONFIRMAR: [
                    CallbackQueryHandler(spx_handler.salvar_registro, pattern="^spx_salvar$"),
                    CallbackQueryHandler(spx_handler.cancelar_registro, pattern="^spx_cancelar$")
                ]
            },
            fallbacks=[
                CommandHandler('cancel', spx_handler.cancelar_registro),
                CallbackQueryHandler(spx_handler.cancelar_registro, pattern="^spx_cancelar$")
            ]
        )

        add(spx_conv, "spx_conversation")
        build_and_add("spx_metas_conversation", spx_metas_handler.get_conversation_handler)
        build_and_add("/spx_hoje", lambda: CommandHandler("spx_hoje", spx_handler.comando_spx_hoje))
        build_and_add("/spx_semana", lambda: CommandHandler("spx_semana", spx_handler.comando_spx_semana))
        build_and_add("/spx_mes", lambda: CommandHandler("spx_mes", spx_handler.comando_spx_mes))
        build_and_add("/spx_metas", lambda: CommandHandler("spx_metas", spx_metas_handler.comando_listar_metas))
        build_and_add("/spx_dashboard", lambda: CommandHandler("spx_dashboard", spx_dashboard.comando_dashboard))
        build_and_add("spx_registro_completo_callback", lambda: CallbackQueryHandler(spx_handler.iniciar_registro_completo, pattern="^spx_registro_completo$"))
        build_and_add("spx_dashboard_callback", lambda: CallbackQueryHandler(spx_dashboard.callback_dashboard, pattern="^spx_dash_"))
    except Exception as exc:
        if safe_mode:
            logger.warning("⚠️ SPX handlers indisponíveis: %s", exc)
        else:
            raise

    logger.info("✅ Handlers padrão registrados")


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

    # Verificação se as credenciais estão presentes
    if not config.TELEGRAM_TOKEN:
        logger.error("❌ Token do Telegram não configurado. Defina a variável de ambiente TELEGRAM_TOKEN.")
        return

    if not config.GEMINI_API_KEY:
        logger.error("❌ Chave da API do Gemini não configurada. Defina a variável de ambiente GEMINI_API_KEY.")
        return

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

    _register_default_handlers(application)
    application.add_error_handler(error_handler)
    logger.info("Todos os handlers adicionados com sucesso.")

    # Configuração e inicialização dos Jobs agendados
    job_queue = application.job_queue
    configurar_jobs(job_queue)
    logger.info("Jobs de metas e agendamentos configurados.")

    return application

def create_application():
    """🔥 CRIA APLICAÇÃO BOT ULTRA-ROBUSTA - SEM TRAVAR"""
    logger.info("🚀 [ULTRA-ROBUST] Criando aplicação bot...")

    # Verificação rápida de credenciais
    if not config.TELEGRAM_TOKEN:
        logger.error("❌ Token do Telegram não configurado")
        return None

    if not config.GEMINI_API_KEY:
        logger.error("❌ Chave da API do Gemini não configurada") 
        return None

    # 🔥 CONFIGURAÇÃO BD ULTRA-ROBUSTA COM TIMEOUT
    try:
        logger.info("🗄️ Configurando banco de dados...")
        criar_tabelas()
        
        # 🔥 NOVA POPULAÇÃO ULTRA-ROBUSTA
        try:
            from database_ultra_robust import verificar_e_popular_se_necessario
            db: Session = next(get_db())
            sucesso = verificar_e_popular_se_necessario(db)
            db.close()
            
            if sucesso:
                logger.info("✅ Dados iniciais OK")
            else:
                logger.warning("⚠️ População dados falhou - continuando")
                
        except Exception as pop_error:
            logger.warning(f"⚠️ Erro população dados: {pop_error} - continuando")
            
        logger.info("✅ Banco de dados pronto.")
        
    except Exception as e:
        logger.error(f"❌ Erro BD: {e} - continuando em modo degradado")

    # 🔥 CONFIGURAÇÃO GEMINI ULTRA-ROBUSTA
    try:
        genai.configure(api_key=config.GEMINI_API_KEY)
        logger.info("✅ API do Gemini configurada.")
    except Exception as e:
        logger.error(f"❌ Erro Gemini: {e} - continuando")

    # 🔥 CRIAÇÃO APLICAÇÃO ULTRA-ROBUSTA
    try:
        application = ApplicationBuilder().token(config.TELEGRAM_TOKEN).build()
        logger.info("✅ Aplicação do bot criada.")

        try:
            _register_default_handlers(application, safe_mode=True)
            logger.info("✅ Handlers padrão adicionados.")
        except Exception as handler_error:
            logger.error(f"❌ Erro handlers: {handler_error}")

        # 🔥 ERROR HANDLER ULTRA-ROBUSTO
        application.add_error_handler(error_handler)

        # 🔥 JOBS ULTRA-ROBUSTOS (OPCIONAL)
        try:
            configurar_jobs(application.job_queue)
            logger.info("✅ Jobs agendados configurados.")
        except Exception as job_error:
            logger.warning(f"⚠️ Jobs falhou: {job_error} - continuando")
        
        # 🏦 OPEN FINANCE AUTO-SYNC
        if OPEN_FINANCE_OAUTH_ENABLED:
            try:
                from open_finance.data_sync import DataSynchronizer
                synchronizer = DataSynchronizer()
                
                # Usar o scheduler existente do bot
                application.job_queue.run_daily(
                    synchronizer.sync_all_connections,
                    time=datetime.strptime("06:00", "%H:%M").time(),
                    name="daily_bank_sync"
                )
                
                # Também rodar a cada 6 horas
                application.job_queue.run_repeating(
                    synchronizer.sync_all_connections,
                    interval=21600,  # 6 horas em segundos
                    first=10,  # Esperar 10 segundos para primeira execução
                    name="periodic_bank_sync"
                )
                
                logger.info("✅ Sincronização automática Open Finance ativada (6h + a cada 6h)")
            except Exception as e:
                logger.error(f"❌ Erro ao agendar sync Open Finance: {e}")
        
        logger.info("🎯 [ULTRA-ROBUST] Aplicação criada com SUCESSO!")
        return application
        
    except Exception as e:
        logger.error(f"❌ [ULTRA-ROBUST] Erro crítico criação: {e}")
        return None

def run_bot():  # pragma: no cover
    """(LEGADO) Execução via polling NÃO utilizada em produção.
    Mantido apenas para debug local isolado. Em produção usamos webhook através do unified_launcher_definitivo.
    """
    logger.warning("⚠️ run_bot() chamado - modo legado de polling. Use unified_launcher_definitivo para produção.")
    application = create_application()
    if application:
        application.run_polling()

if __name__ == '__main__':  # pragma: no cover
    run_bot()