"""
Sistema de Jobs e Tarefas Agendadas - MaestroFin
"""
import logging
from datetime import datetime, time
from telegram.ext import ContextTypes
from alerts import agendar_notificacoes_diarias, checar_objetivos_semanal
from gerente_financeiro.assistente_proativo import job_assistente_proativo
from gerente_financeiro.wrapped_anual import job_wrapped_anual

logger = logging.getLogger(__name__)

async def sync_all_users_transactions(context: ContextTypes.DEFAULT_TYPE):
    """Job que sincroniza transações de todos os usuários ativos"""
    db = None
    try:
        logger.info("🔄 Iniciando sincronização automática de transações...")
        
        from database.database import get_db
        from models import Usuario, PluggyItem
        from gerente_financeiro.open_finance_oauth_handler import sync_all_transactions_for_user
        
        db = next(get_db())
        
        # Buscar todos usuários com items ativos
        usuarios_com_items = (
            db.query(Usuario)
            .join(PluggyItem, Usuario.id == PluggyItem.id_usuario)
            .filter(PluggyItem.status.in_(["UPDATED", "PARTIAL_SUCCESS"]))
            .distinct()
            .all()
        )
        
        if not usuarios_com_items:
            logger.info("ℹ️  Nenhum usuário com Open Finance ativo para sincronizar")
            return
        
        total_synced = 0
        total_new = 0
        
        for usuario in usuarios_com_items:
            try:
                stats = sync_all_transactions_for_user(usuario.telegram_id, days=7)
                
                if "error" not in stats:
                    new_txns = stats.get("new", 0)
                    total_new += new_txns
                    total_synced += 1
                    
                    # Notificar usuário se houver transações novas
                    if new_txns > 0:
                        try:
                            await context.bot.send_message(
                                chat_id=usuario.telegram_id,
                                text=(
                                    f"🔔 *Nova\\(s\\) transação\\(ões\\)\\!*\n\n"
                                    f"Encontrei *{new_txns} nova\\(s\\) transação\\(ões\\)* nas suas contas\\.\n\n"
                                    f"Use /importar\\_transacoes para revisar e importar\\."
                                ),
                                parse_mode="MarkdownV2"
                            )
                        except Exception as e:
                            logger.error(f"❌ Erro ao notificar usuário {usuario.telegram_id}: {e}")
                
            except Exception as e:
                logger.error(f"❌ Erro ao sincronizar usuário {usuario.telegram_id}: {e}")
                continue
        
        logger.info(
            f"✅ Sincronização automática concluída: "
            f"{total_synced} usuários, {total_new} transações novas"
        )
        
    except Exception as e:
        logger.error(f"❌ Erro no job de sincronização: {e}", exc_info=True)
    finally:
        if db:
            db.close()


def configurar_jobs(job_queue):
    """Configura todos os jobs agendados do sistema"""
    try:
        logger.info("⚙️ Configurando jobs agendados...")
        
        # Job diário às 01:00 - Agendamento de notificações
        job_queue.run_daily(
            agendar_notificacoes_diarias,
            time=time(hour=1, minute=0),
            name="agendador_mestre_diario"
        )
        
        # Job semanal aos sábados às 10:00 - Verificar objetivos
        job_queue.run_daily(
            checar_objetivos_semanal,
            time=time(hour=10, minute=0),
            days=(6,),  # Sábado
            name="checar_metas_semanalmente"
        )
        
        # Job a cada 1 hora - Sincronizar transações Open Finance
        job_queue.run_repeating(
            sync_all_users_transactions,
            interval=3600,  # 1 hora em segundos
            first=60,  # Primeira execução após 1 minuto do startup
            name="sync_open_finance_transactions"
        )
        
        # Job diário às 20:00 - Assistente Proativo (alertas inteligentes)
        job_queue.run_daily(
            job_assistente_proativo,
            time=time(hour=20, minute=0),
            name="assistente_proativo_diario"
        )
        
        # Job anual 31/dez às 13:00 - Wrapped Financeiro do Ano
        from apscheduler.triggers.cron import CronTrigger
        job_queue.run_daily(
            job_wrapped_anual,
            time=time(hour=13, minute=0),
            days=(30,),  # Dia 31 (0-indexed, então 30 = 31)
            name="wrapped_anual_31_dezembro"
        )
        
        logger.info("✅ Jobs agendados configurados com sucesso:")
        logger.info("   📅 Notificações diárias: 01:00")
        logger.info("   🎯 Verificação de metas: Sábado 10:00")
        logger.info("   🔄 Sincronização Open Finance: A cada 1 hora")
        logger.info("   🤖 Assistente Proativo: 20:00 (alertas inteligentes)")
        logger.info("   🎊 Wrapped Anual: 31/dez 13:00 (retrospectiva do ano)")
        
    except Exception as e:
        logger.error(f"❌ Erro ao configurar jobs: {e}")
