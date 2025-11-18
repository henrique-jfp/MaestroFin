"""
🔄 Sincronizador Automático de Dados Bancários
Job que roda periodicamente para atualizar saldos e transações
"""

import logging
from datetime import datetime
from open_finance.bank_connector import BankConnector
from telegram.ext import ContextTypes
from database.database import Database

logger = logging.getLogger(__name__)


class DataSynchronizer:
    """Sincronizador automático de dados bancários"""
    
    def __init__(self):
        self.connector = BankConnector()
        self.db = Database()
    
    async def sync_all_connections(self, context: ContextTypes.DEFAULT_TYPE | None = None):
        """
        Sincroniza todas as conexões ativas
        Chamado automaticamente via APScheduler
        """
        logger.info("🔄 Iniciando sincronização automática de dados bancários...")
        
        try:
            # Buscar todas as conexões ativas
            query = """
                SELECT id, item_id, user_id, connector_name
                FROM bank_connections
                WHERE status IN ('UPDATED', 'LOGIN_ERROR')
                ORDER BY last_sync_at ASC NULLS FIRST
                LIMIT 100
            """
            
            connections = self.db.execute_query(query, fetch=True)
            
            if not connections:
                logger.info("ℹ️ Nenhuma conexão para sincronizar")
                return
            
            success_count = 0
            error_count = 0
            
            for conn_row in connections:
                conn_id, item_id, user_id, bank_name = conn_row
                
                try:
                    logger.info(f"🔄 Sincronizando {bank_name} (user {user_id})...")
                    
                    # Sincronizar contas (atualiza saldos)
                    self.connector._sync_accounts(conn_id, item_id)
                    
                    # Sincronizar transações (últimos 7 dias)
                    self.connector.sync_transactions(conn_id, days=7)
                    
                    success_count += 1
                    logger.info(f"✅ {bank_name} sincronizado com sucesso")
                    
                except Exception as e:
                    error_count += 1
                    logger.error(f"❌ Erro ao sincronizar {bank_name}: {e}", exc_info=True)
            
            logger.info(
                f"✅ Sincronização concluída: "
                f"{success_count} sucesso, {error_count} erros"
            )
            
        except Exception as e:
            logger.error(f"❌ Erro na sincronização automática: {e}", exc_info=True)
            # NÃO fazer raise - isso quebraria o job scheduler
    
    async def sync_user_connections(self, user_id: int):
        """
        Sincroniza todas as conexões de um usuário específico
        
        Args:
            user_id: ID do usuário Telegram
        """
        logger.info(f"🔄 Sincronizando conexões do usuário {user_id}...")
        
        try:
            connections = self.connector.list_connections(user_id)
            
            for conn in connections:
                try:
                    self.connector._sync_accounts(conn['id'], conn['item_id'])
                    self.connector.sync_transactions(conn['id'], days=30)
                except Exception as e:
                    logger.error(f"❌ Erro ao sincronizar {conn['connector_name']}: {e}")
            
            logger.info(f"✅ Sincronização do usuário {user_id} concluída")
            
        except Exception as e:
            logger.error(f"❌ Erro ao sincronizar usuário {user_id}: {e}")
            raise


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
