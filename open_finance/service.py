"""
open_finance/service.py

Módulo de Serviço para Open Finance.
Responsabilidade Única: Orquestrar a lógica de negócio do Open Finance.
Utiliza o PluggyClient para buscar dados da API e os repositórios (models)
para persistir e consultar dados no banco de dados local.
"""
import logging
from typing import List, Dict, Tuple, Optional
from sqlalchemy.orm import Session, joinedload
from datetime import datetime, timedelta

from .pluggy_client import PluggyClient, PluggyClientError
from models import Usuario, PluggyItem, PluggyAccount, PluggyTransaction

logger = logging.getLogger(__name__)

# Paleta visual para logs e mensagens
PALETA = {
    "azul": "#0A2540",
    "cinza": "#F5F7FA",
    "destaque": "#3E7BFA",
    "dourado": "#F2C94C",
    "grafite": "#1B1F23"
}

def log_sucesso(msg):
    logger.info(f"\033[1;34m✅ {msg}\033[0m")

def log_erro(msg):
    logger.error(f"\033[1;31m❌ {msg}\033[0m")

def log_aviso(msg):
    logger.warning(f"\033[1;33m⚠️ {msg}\033[0m")

def log_destaque(msg):
    logger.info(f"\033[1;36m✨ {msg}\033[0m")

import asyncio

async def _fetch_and_process_transactions(client: PluggyClient, account: PluggyAccount, from_date: str, session: Session) -> int:
    """Função auxiliar para buscar e processar transações de UMA conta de forma assíncrona."""
    new_tx_count = 0
    try:
        transactions_data = await asyncio.to_thread(client.list_transactions, account.pluggy_account_id, from_date)
        for tx_data in transactions_data:
            existing_tx = session.query(PluggyTransaction).filter(PluggyTransaction.pluggy_transaction_id == tx_data['id']).first()
            if not existing_tx:
                date_str = tx_data['date']
                try:
                    date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00')).date()
                except ValueError:
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()

                new_tx = PluggyTransaction(
                    id_account=account.id,
                    pluggy_transaction_id=tx_data['id'],
                    description=tx_data['description'],
                    amount=tx_data['amount'],
                    date=date_obj,
                    type=tx_data.get('type'),
                    category=tx_data.get('category'),
                    merchant_name=tx_data.get('merchantName')
                )
                session.add(new_tx)
                new_tx_count += 1
        log_sucesso(f"{new_tx_count} novas transações sincronizadas para a conta {account.pluggy_account_id}.")
    except PluggyClientError as e:
        log_erro(f"Erro ao sincronizar conta {account.pluggy_account_id}: {e}")
    return new_tx_count


class OpenFinanceService:
    """Serviço principal para operações do Open Finance."""

    def __init__(self, db_session: Session):
        self.db = db_session
        self.client = PluggyClient()

    def get_user_by_telegram_id(self, telegram_id: int) -> Optional[Usuario]:
        """Busca um usuário pelo seu ID do Telegram."""
        return self.db.query(Usuario).filter(Usuario.telegram_id == telegram_id).first()

    def get_user_connections(self, user_id: int) -> List[PluggyItem]:
        """Busca as conexões de Open Finance de um usuário no banco de dados."""
        usuario = self.get_user_by_telegram_id(user_id)
        if not usuario:
            log_aviso(f"Usuário {user_id} não encontrado para buscar conexões Open Finance.")
            return []
        conexoes = self.db.query(PluggyItem).filter(PluggyItem.id_usuario == usuario.id).all()
        log_destaque(f"{len(conexoes)} conexões encontradas para o usuário {user_id}.")
        return conexoes

    def create_connection_item(self, user_id: int, connector_id: int, cpf: str) -> Dict:
        """Cria um 'item' na Pluggy API, sem salvar no banco ainda."""
        parameters = {"cpf": cpf}
        item_data = self.client.create_item(connector_id, parameters)
        return item_data

    def get_item_status(self, item_id: str) -> Dict:
        """Consulta o status de um 'item' na API da Pluggy."""
        return self.client.get_item(item_id)

    def save_connection_details(self, user_id: int, item_data: Dict) -> PluggyItem:
        """Salva os detalhes de uma conexão (item) bem-sucedida no banco de dados."""
        usuario = self.get_user_by_telegram_id(user_id)
        if not usuario:
            log_erro(f"Usuário com telegram_id {user_id} não encontrado ao salvar conexão.")
            raise ValueError(f"Usuário com telegram_id {user_id} não encontrado.")

        existing_item = self.db.query(PluggyItem).filter(PluggyItem.pluggy_item_id == item_data['id']).first()
        
        connector_data = item_data.get('connector', {})
        
        if existing_item:
            existing_item.status = item_data.get('status', existing_item.status)
            existing_item.last_updated_at = datetime.now()
            self.db.commit()
            self.db.refresh(existing_item)
            log_sucesso(f"Conexão {existing_item.connector_name} atualizada para o usuário {usuario.id}.")
            return existing_item
        else:
            new_item = PluggyItem(
                id_usuario=usuario.id,
                pluggy_item_id=item_data['id'],
                connector_id=connector_data.get('id'),
                connector_name=connector_data.get('name'),
                status=item_data.get('status'),
                last_updated_at=datetime.now()
            )
            self.db.add(new_item)
            self.db.commit()
            self.db.refresh(new_item)
            log_sucesso(f"Nova conexão {new_item.connector_name} criada para o usuário {usuario.id}.")
            return new_item

    def sync_accounts_for_item(self, pluggy_item: PluggyItem) -> Tuple[int, int]:
        """Sincroniza as contas de um item específico, incluindo dados de cartão."""
        accounts_data = self.client.list_accounts(pluggy_item.pluggy_item_id)
        new_accounts = 0
        updated_accounts = 0
        for acc_data in accounts_data:
            existing_account = self.db.query(PluggyAccount).filter(PluggyAccount.pluggy_account_id == acc_data['id']).first()
            account_to_update = existing_account or PluggyAccount(id_item=pluggy_item.id, pluggy_account_id=acc_data['id'])
            account_to_update.type = acc_data.get('type')
            account_to_update.subtype = acc_data.get('subtype')
            account_to_update.name = acc_data.get('name')
            account_to_update.balance = acc_data.get('balance')
            account_to_update.currency_code = acc_data.get('currencyCode', 'BRL')
            account_to_update.number = acc_data.get('number')
            if acc_data.get('type') == 'CREDIT':
                try:
                    credit_data = self.client.get_credit_card(acc_data['id'])
                    account_to_update.credit_limit = credit_data.get('limit')
                    account_to_update.balance = credit_data.get('balance', acc_data.get('balance'))
                    account_to_update.credit_level = credit_data.get('level')
                    account_to_update.credit_brand = credit_data.get('brand')
                    account_to_update.credit_closing_date = credit_data.get('closingDate')
                    account_to_update.credit_due_date = credit_data.get('dueDate')
                except PluggyClientError as e:
                    log_aviso(f"Não foi possível obter detalhes do cartão de crédito para a conta {acc_data['id']}: {e}")
                    account_to_update.credit_limit = acc_data.get('creditLimit')
            if not existing_account:
                self.db.add(account_to_update)
                new_accounts += 1
            else:
                updated_accounts += 1
        self.db.commit()
        log_sucesso(f"{new_accounts} novas contas e {updated_accounts} contas atualizadas para o item {pluggy_item.connector_name}.")
        return new_accounts, updated_accounts

    async def sync_transactions_for_user_async(self, user_id: int, days: int = 60) -> Dict[str, int]:
        """Sincroniza transações de forma massivamente paralela."""
        connections = self.get_user_connections(user_id)
        if not connections:
            log_aviso(f"Nenhuma conexão encontrada para o usuário {user_id} ao sincronizar transações.")
            return {"accounts": 0, "new_transactions": 0}

        from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        all_accounts = [acc for conn in connections for acc in conn.accounts]
        if not all_accounts:
            log_aviso(f"Nenhuma conta encontrada para o usuário {user_id} ao sincronizar transações.")
            return {"accounts": 0, "new_transactions": 0}

        # CORREÇÃO: Cada tarefa deve ter sua própria sessão de banco de dados
        # para evitar conflitos de concorrência
        async def _fetch_and_process_with_session(account, from_date):
            """Wrapper que cria sua própria sessão de banco para evitar conflitos."""
            from database.database import get_db
            db_session = next(get_db())
            try:
                result = await _fetch_and_process_transactions(self.client, account, from_date, db_session)
                if result > 0:
                    db_session.commit()
                return result
            finally:
                db_session.close()

        # Cria uma tarefa para cada conta e as executa em paralelo
        tasks = [_fetch_and_process_with_session(acc, from_date) for acc in all_accounts]
        results = await asyncio.gather(*tasks)

        total_new_txns = sum(results)
        log_sucesso(f"Sincronização concluída: {len(all_accounts)} contas, {total_new_txns} novas transações para o usuário {user_id}.")
        return {"accounts": len(all_accounts), "new_transactions": total_new_txns}

    def sync_transactions_for_user(self, user_id: int, days: int = 60) -> Dict[str, int]:
        """Sincroniza transações de todas as contas conectadas de um usuário."""
        connections = self.get_user_connections(user_id)
        if not connections:
            log_aviso(f"Nenhuma conexão encontrada para o usuário {user_id} ao sincronizar transações.")
            return {"accounts": 0, "new_transactions": 0}

        total_new_txns = 0
        from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        for conn in connections:
            accounts = self.db.query(PluggyAccount).filter(PluggyAccount.id_item == conn.id).all()
            for acc in accounts:
                try:
                    transactions_data = self.client.list_transactions(acc.pluggy_account_id, from_date)
                    for tx_data in transactions_data:
                        existing_tx = self.db.query(PluggyTransaction).filter(PluggyTransaction.pluggy_transaction_id == tx_data['id']).first()
                        if not existing_tx:
                            date_str = tx_data['date']
                            try:
                                date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00')).date()
                            except ValueError:
                                date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
                            new_tx = PluggyTransaction(
                                id_account=acc.id,
                                pluggy_transaction_id=tx_data['id'],
                                description=tx_data['description'],
                                amount=tx_data['amount'],
                                date=date_obj,
                                type=tx_data.get('type'),
                                category=tx_data.get('category'),
                                merchant_name=tx_data.get('merchantName')
                            )
                            self.db.add(new_tx)
                            total_new_txns += 1
                    log_sucesso(f"{len(transactions_data)} transações sincronizadas para a conta {acc.pluggy_account_id}.")
                except PluggyClientError as e:
                    log_erro(f"Erro ao sincronizar transações para a conta {acc.pluggy_account_id}: {e}")
                    continue
        self.db.commit()
        log_sucesso(f"Sincronização concluída: {len(connections)} conexões, {total_new_txns} novas transações para o usuário {user_id}.")
        return {"accounts": len(connections), "new_transactions": total_new_txns}
        
    def get_pending_transactions(self, user_id: int) -> List[PluggyTransaction]:
        """Busca transações do Open Finance que ainda não foram importadas para os lançamentos principais."""
        usuario = self.get_user_by_telegram_id(user_id)
        if not usuario:
            log_aviso(f"Usuário {user_id} não encontrado ao buscar transações pendentes.")
            return []
        pendentes = (
            self.db.query(PluggyTransaction)
            .join(PluggyAccount, PluggyTransaction.id_account == PluggyAccount.id)
            .join(PluggyItem, PluggyAccount.id_item == PluggyItem.id)
            .filter(PluggyItem.id_usuario == usuario.id)
            .filter(PluggyTransaction.imported_to_lancamento == False)
            .order_by(PluggyTransaction.date.desc())
            .all()
        )
        log_destaque(f"{len(pendentes)} transações pendentes encontradas para o usuário {user_id}.")
        return pendentes
