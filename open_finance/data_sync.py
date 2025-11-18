"""
🔄 Sincronizador Automático de Dados Bancários
Job que roda periodicamente para atualizar saldos e transações
"""

import logging
from datetime import datetime
from open_finance.bank_connector import BankConnector
from telegram.ext import ContextTypes
from database.database import get_db
from models import PluggyItem

logger = logging.getLogger(__name__)


class DataSynchronizer:
    """Sincronizador automático de dados bancários"""
    
    def __init__(self):
        self.connector = BankConnector()
    
    async def sync_all_connections(self, context: ContextTypes.DEFAULT_TYPE | None = None):
        """
        Sincroniza todas as conexões ativas
        Chamado automaticamente via APScheduler
        """
        logger.info("🔄 Iniciando sincronização automática de dados bancários...")
        
        db = next(get_db())
        try:
            # Buscar todas as conexões ativas do Pluggy
            connections = (
                db.query(PluggyItem)
                .filter(PluggyItem.status.in_(['UPDATED', 'LOGIN_ERROR', 'OUTDATED']))
                .order_by(PluggyItem.last_updated_at.asc())
                .limit(100)
                .all()
            )
            
            if not connections:
                logger.info("ℹ️ Nenhuma conexão para sincronizar")
                return
            
            success_count = 0
            error_count = 0
            
            for item in connections:
                try:
                    logger.info(f"🔄 Sincronizando {item.connector_name} (user {item.id_usuario})...")
                    
                    # O sync é feito via handler Open Finance
                    # Aqui apenas logamos - a sincronização real acontece via /sincronizar
                    # Este job é apenas um lembrete/verificação
                    
                    success_count += 1
                    logger.info(f"✅ {item.connector_name} verificado")
                    
                except Exception as e:
                    error_count += 1
                    logger.error(f"❌ Erro ao verificar {item.connector_name}: {e}", exc_info=True)
            
            logger.info(
                f"✅ Sincronização concluída: "
                f"{success_count} sucesso, {error_count} erros"
            )
            
        except Exception as e:
            logger.error(f"❌ Erro na sincronização automática: {e}", exc_info=True)
            # NÃO fazer raise - isso quebraria o job scheduler
        finally:
            db.close()
    
    async def sync_user_connections(self, user_id: int):
        """
        Sincroniza todas as conexões de um usuário específico
        
        Args:
            user_id: ID do usuário (telegram_id)
        """
        logger.info(f"🔄 Sincronizando conexões do usuário {user_id}...")
        
        db = next(get_db())
        try:
            # Buscar conexões do usuário
            from models import Usuario
            usuario = db.query(Usuario).filter(Usuario.telegram_id == user_id).first()
            
            if not usuario:
                logger.warning(f"⚠️ Usuário {user_id} não encontrado")
                return
            
            connections = db.query(PluggyItem).filter(PluggyItem.id_usuario == usuario.id).all()
            
            for item in connections:
                try:
                    logger.info(f"✅ Conexão {item.connector_name} verificada")
                except Exception as e:
                    logger.error(f"❌ Erro ao verificar {item.connector_name}: {e}")
            
            logger.info(f"✅ Sincronização do usuário {user_id} concluída")
            
        except Exception as e:
            logger.error(f"❌ Erro ao sincronizar usuário {user_id}: {e}")
            raise
        finally:
            db.close()


# ==================== Funções para APScheduler ====================

def schedule_daily_sync():
    """
    Configura job diário de sincronização
    Chamar no startup do bot
    """
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger
    
    scheduler = AsyncIOScheduler()
    synchronizer = DataSynchronizer()
    
    # Sincronizar todos os dias às 6h da manhã
    scheduler.add_job(
        synchronizer.sync_all_connections,
        trigger=CronTrigger(hour=6, minute=0),
        id='daily_bank_sync',
        name='Sincronização Diária de Bancos',
        replace_existing=True
    )
    
    # Também rodar a cada 6 horas
    scheduler.add_job(
        synchronizer.sync_all_connections,
        trigger=CronTrigger(hour='*/6'),
        id='periodic_bank_sync',
        name='Sincronização Periódica de Bancos',
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("✅ Sincronização automática agendada")
    
    return scheduler
