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
from datetime import datetime

from .pluggy_client import PluggyClient, PluggyClientError
from models import Usuario, PluggyItem, PluggyAccount, PluggyTransaction

logger = logging.getLogger(__name__)

class OpenFinanceService:
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
            return []
        return self.db.query(PluggyItem).filter(PluggyItem.id_usuario == usuario.id).all()

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
            raise ValueError(f"Usuário com telegram_id {user_id} não encontrado.")

        existing_item = self.db.query(PluggyItem).filter(PluggyItem.pluggy_item_id == item_data['id']).first()
        
        connector_data = item_data.get('connector', {})
        
        if existing_item:
            existing_item.status = item_data.get('status', existing_item.status)
            existing_item.last_updated_at = datetime.now()
            self.db.commit()
            self.db.refresh(existing_item)
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
            return new_item

    def sync_accounts_for_item(self, pluggy_item: PluggyItem) -> Tuple[int, int]:
        """Sincroniza as contas de um item específico."""
        accounts_data = self.client.list_accounts(pluggy_item.pluggy_item_id)
        
        new_accounts = 0
        updated_accounts = 0

        for acc_data in accounts_data:
            existing_account = self.db.query(PluggyAccount).filter(PluggyAccount.pluggy_account_id == acc_data['id']).first()
            if existing_account:
                existing_account.balance = acc_data.get('balance')
                updated_accounts += 1
            else:
                new_account = PluggyAccount(
                    id_item=pluggy_item.id,
                    pluggy_account_id=acc_data['id'],
                    type=acc_data.get('type'),
                    subtype=acc_data.get('subtype'),
                    name=acc_data.get('name'),
                    balance=acc_data.get('balance'),
                    credit_limit=acc_data.get('creditLimit'),
                    currency_code=acc_data.get('currencyCode', 'BRL'),
                    number=acc_data.get('number')
                )
                self.db.add(new_account)
                new_accounts += 1
        
        self.db.commit()
        return new_accounts, updated_accounts

    def sync_transactions_for_user(self, user_id: int, days: int = 30) -> Dict[str, int]:
        """Sincroniza transações de todas as contas conectadas de um usuário."""
        connections = self.get_user_connections(user_id)
        if not connections:
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
                            new_tx = PluggyTransaction(
                                id_account=acc.id,
                                pluggy_transaction_id=tx_data['id'],
                                description=tx_data['description'],
                                amount=tx_data['amount'],
                                date=datetime.strptime(tx_data['date'], "%Y-%m-%d").date(),
                                type=tx_data.get('type'),
                                category=tx_data.get('category'),
                                merchant_name=tx_data.get('merchantName')
                            )
                            self.db.add(new_tx)
                            total_new_txns += 1
                except PluggyClientError as e:
                    logger.error(f"Erro ao sincronizar transações para a conta {acc.pluggy_account_id}: {e}")
                    continue # Pula para a próxima conta em caso de erro

        self.db.commit()
        return {"accounts": len(connections), "new_transactions": total_new_txns}
        
    def get_pending_transactions(self, user_id: int) -> List[PluggyTransaction]:
        """Busca transações do Open Finance que ainda não foram importadas para os lançamentos principais."""
        usuario = self.get_user_by_telegram_id(user_id)
        if not usuario:
            return []
            
        return (
            self.db.query(PluggyTransaction)
            .join(PluggyAccount, PluggyTransaction.id_account == PluggyAccount.id)
            .join(PluggyItem, PluggyAccount.id_item == PluggyItem.id)
            .filter(PluggyItem.id_usuario == usuario.id)
            .filter(PluggyTransaction.imported_to_lancamento == False)
            .order_by(PluggyTransaction.date.desc())
            .all()
        )
