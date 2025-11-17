"""
🔗 Gerenciador de Conexões Bancárias
Gerencia conexões de usuários com instituições financeiras
"""

import json
import logging
import time
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from database.database import SessionLocal, engine
from sqlalchemy import text
from .pluggy_client import PluggyClient

logger = logging.getLogger(__name__)


class BankConnectorError(Exception):
    """Exceção base para erros de conexão bancária."""


class BankConnectorUserActionRequired(BankConnectorError):
    """Indica que o banco requer ação adicional do usuário (ex.: OTP)."""

    def __init__(self, message: str, detail: Optional[str] = None, *, item: Optional[Dict] = None):
        super().__init__(message)
        self.detail = detail
        self.item = item or {}


class BankConnectorAdditionalAuthRequired(BankConnectorUserActionRequired):
    """Indica que o banco pediu dados extras (ex.: OTP, token, pergunta secreta)."""

    def __init__(
        self,
        message: str,
        detail: Optional[str] = None,
        *,
        item: Optional[Dict] = None,
        form: Optional[Dict] = None,
        next_step: Optional[str] = None,
        insights: Optional[Dict] = None,
    ):
        super().__init__(message, detail, item=item)
        self.form = form or {}
        self.next_step = next_step
        self.insights = insights or {}


class BankConnectorTimeout(BankConnectorError):
    """Indica que o tempo de espera pela instituição estourou."""


class BankConnector:
    """Gerenciador de conexões bancárias por usuário"""
    
    def __init__(self):
        self.client = PluggyClient()
        self._ensure_tables()
    
    def _ensure_tables(self):
        """Cria tabelas se não existirem"""
        queries = [
            # Tabela de conexões (items)
            """
            CREATE TABLE IF NOT EXISTS bank_connections (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                item_id VARCHAR(255) NOT NULL UNIQUE,
                connector_id INTEGER NOT NULL,
                connector_name VARCHAR(255),
                status VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_sync_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES usuarios(telegram_id) ON DELETE CASCADE
            )
            """,
            
            # Tabela de contas bancárias
            """
            CREATE TABLE IF NOT EXISTS bank_accounts (
                id SERIAL PRIMARY KEY,
                connection_id INTEGER NOT NULL,
                account_id VARCHAR(255) NOT NULL UNIQUE,
                account_type VARCHAR(50),
                account_number VARCHAR(100),
                account_name VARCHAR(255),
                balance DECIMAL(15, 2),
                currency VARCHAR(10) DEFAULT 'BRL',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (connection_id) REFERENCES bank_connections(id) ON DELETE CASCADE
            )
            """,
            
            # Tabela de transações sincronizadas
            """
            CREATE TABLE IF NOT EXISTS bank_transactions (
                id SERIAL PRIMARY KEY,
                account_id INTEGER NOT NULL,
                transaction_id VARCHAR(255) NOT NULL UNIQUE,
                description VARCHAR(500),
                amount DECIMAL(15, 2) NOT NULL,
                date DATE NOT NULL,
                type VARCHAR(50),
                category VARCHAR(100),
                merchant_name VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (account_id) REFERENCES bank_accounts(id) ON DELETE CASCADE
            )
            """,
            
            # Índices para performance
            "CREATE INDEX IF NOT EXISTS idx_bank_connections_user ON bank_connections(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_bank_accounts_connection ON bank_accounts(connection_id)",
            "CREATE INDEX IF NOT EXISTS idx_bank_transactions_account ON bank_transactions(account_id)",
            "CREATE INDEX IF NOT EXISTS idx_bank_transactions_date ON bank_transactions(date DESC)"
        ]
        
        try:
            with engine.connect() as conn:
                for query in queries:
                    conn.execute(text(query))
                conn.commit()
            logger.info("✅ Tabelas Open Finance criadas/verificadas")
        except Exception as e:
            logger.error(f"❌ Erro ao criar tabelas: {e}")
            # Não raise - deixa bot funcionar mesmo sem Open Finance
            logger.warning("⚠️ Open Finance indisponível (sem tabelas)")
    
    # ==================== CONEXÕES ====================
    
    def create_connection(
        self, 
        user_id: int, 
        connector_id: int,
        credentials: Dict
    ) -> Dict:
        """
        Cria nova conexão bancária para usuário
        
        Args:
            user_id: ID do usuário Telegram
            connector_id: ID do conector (banco)
            credentials: Credenciais de login
            
        Returns:
            Dados da conexão criada
        """
        logger.info(f"🔗 Criando conexão para usuário {user_id}...")
        
        try:
            # Criar item no Pluggy
            item = self.client.create_item(connector_id, credentials)
            item_id = item['id']

            # Aguardar processamento pelo banco antes de seguir
            final_item = self._wait_until_ready(item_id)
            status = final_item.get('status')
            status_detail = final_item.get('statusDetail')
            
            # Obter nome do conector
            connector = self.client.get_connector(connector_id)
            connector_name = connector.get('name', 'Desconhecido')
            
            # Salvar no banco
            with engine.connect() as conn:
                result = conn.execute(
                    text("""
                        INSERT INTO bank_connections 
                            (user_id, item_id, connector_id, connector_name, status)
                        VALUES (:user_id, :item_id, :connector_id, :connector_name, :status)
                        RETURNING id, item_id, connector_name, status, created_at
                    """),
                    {
                        "user_id": user_id,
                        "item_id": item_id,
                        "connector_id": connector_id,
                        "connector_name": connector_name,
                        "status": status
                    }
                )
                conn.commit()
                row = result.fetchone()
                
                if row:
                    connection_id = row[0]
                    logger.info(f"✅ Conexão criada: {row[1]} (status {status})")
                    
                    # Sincronizar contas imediatamente
                    self._sync_accounts(connection_id, item_id)
                    
                    return {
                        'id': row[0],
                        'item_id': row[1],
                        'connector_name': row[2],
                        'status': row[3],
                        'created_at': row[4],
                        'status_detail': status_detail
                    }
            
            raise Exception("Erro ao salvar conexão no banco")
            
        except BankConnectorAdditionalAuthRequired as action_err:
            logger.warning("⚠️ Banco solicitou credenciais adicionais (OTP/token)")
            raise
        except BankConnectorUserActionRequired as action_err:
            logger.warning(f"⚠️ Ação adicional requerida pelo banco: {action_err.detail}")
            raise
        except BankConnectorTimeout as timeout_err:
            logger.error(f"⏱️ Tempo excedido aguardando retorno do banco: {timeout_err}")
            try:
                self.client.delete_item(item_id)
            except Exception:
                logger.debug("Não foi possível remover item após timeout")
            raise
        except Exception as e:
            logger.error(f"❌ Erro ao criar conexão: {e}")
            try:
                if 'item_id' in locals():
                    self.client.delete_item(item_id)
            except Exception:
                logger.debug("Não foi possível remover item após erro")
            raise
    
    def list_connections(self, user_id: int) -> List[Dict]:
        """Lista todas as conexões bancárias de um usuário"""
        with engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT id, item_id, connector_name, status, created_at, last_sync_at
                    FROM bank_connections
                    WHERE user_id = :user_id
                    ORDER BY created_at DESC
                """),
                {"user_id": user_id}
            )
            
            connections = []
            for row in result:
                connections.append({
                    'id': row[0],
                    'item_id': row[1],
                    'connector_name': row[2],
                    'status': row[3],
                    'created_at': row[4],
                    'last_sync_at': row[5]
                })
            
            return connections
    
    def get_connection(self, connection_id: int) -> Optional[Dict]:
        """Obtém detalhes de uma conexão específica"""
        with engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT id, user_id, item_id, connector_name, status, created_at, last_sync_at
                    FROM bank_connections
                    WHERE id = :connection_id
                """),
                {"connection_id": connection_id}
            )
            
            row = result.fetchone()
            if row:
                return {
                    'id': row[0],
                    'user_id': row[1],
                    'item_id': row[2],
                    'connector_name': row[3],
                    'status': row[4],
                    'created_at': row[5],
                    'last_sync_at': row[6]
                }
            
            return None
    
    def delete_connection(self, connection_id: int) -> bool:
        """Remove conexão bancária"""
        try:
            # Obter item_id
            connection = self.get_connection(connection_id)
            if not connection:
                return False
            
            # Remover do Pluggy
            self.client.delete_item(connection['item_id'])
            
            # Remover do banco (cascade remove contas e transações)
            with engine.connect() as conn:
                conn.execute(
                    text("DELETE FROM bank_connections WHERE id = :connection_id"),
                    {"connection_id": connection_id}
                )
                conn.commit()
            
            logger.info(f"✅ Conexão {connection_id} removida")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao remover conexão: {e}")
            return False
    
    # ==================== CONTAS ====================
    
    def _sync_accounts(self, connection_id: int, item_id: str):
        """Sincroniza contas bancárias de uma conexão"""
        logger.info(f"💳 Sincronizando contas da conexão {connection_id}...")
        
        try:
            accounts = self.client.list_accounts(item_id)
            
            with engine.connect() as conn:
                for account in accounts:
                    conn.execute(
                        text("""
                            INSERT INTO bank_accounts 
                                (connection_id, account_id, account_type, account_number, 
                                 account_name, balance, currency)
                            VALUES (:connection_id, :account_id, :account_type, :account_number,
                                    :account_name, :balance, :currency)
                            ON CONFLICT (account_id) 
                            DO UPDATE SET
                                balance = EXCLUDED.balance,
                                updated_at = CURRENT_TIMESTAMP
                        """),
                        {
                            "connection_id": connection_id,
                            "account_id": account['id'],
                            "account_type": account.get('type'),
                            "account_number": account.get('number'),
                            "account_name": account.get('name'),
                            "balance": account.get('balance'),
                            "currency": account.get('currencyCode', 'BRL')
                        }
                    )
                
                # Atualizar timestamp de sincronização
                conn.execute(
                    text("""
                        UPDATE bank_connections 
                        SET last_sync_at = CURRENT_TIMESTAMP
                        WHERE id = :connection_id
                    """),
                    {"connection_id": connection_id}
                )
                conn.commit()
            
            logger.info(f"✅ {len(accounts)} contas sincronizadas")
            
        except Exception as e:
            logger.error(f"❌ Erro ao sincronizar contas: {e}")
            raise

    def _wait_until_ready(self, item_id: str, timeout: int = 90, interval: int = 4) -> Dict:
        """Espera a instituição responder com sucesso ou erro."""
        start = time.time()
        last_status = None
        last_detail = None

        while time.time() - start < timeout:
            item = self.client.get_item(item_id)
            status = item.get('status')
            detail = item.get('statusDetail')
            next_step = item.get('nextStep')
            parameter_form = item.get('parameterForm') or {}
            connector_insights = item.get('connectorInsights') or {}
            provider_message = connector_insights.get('providerMessage')

            if status != last_status:
                logger.info(
                    "⌛ Status item %s: %s (detail=%s, next_step=%s)",
                    item_id,
                    status,
                    detail,
                    next_step,
                )
                last_status = status
                last_detail = detail

            if status in {"HEALTHY", "PARTIAL_SUCCESS"}:
                return item

            if status == "WAITING_USER_INPUT":
                action_links: List[str] = []
                link_candidates = [
                    connector_insights.get('authorizationUrl') if isinstance(connector_insights, dict) else None,
                    connector_insights.get('providerUrl') if isinstance(connector_insights, dict) else None,
                    connector_insights.get('authUrl') if isinstance(connector_insights, dict) else None,
                    connector_insights.get('linkUrl') if isinstance(connector_insights, dict) else None,
                    item.get('linkUrl'),
                ]

                for candidate in link_candidates:
                    if isinstance(candidate, str) and candidate.startswith("http"):
                        action_links.append(candidate)

                message = (
                    detail
                    or provider_message
                    or (next_step if isinstance(next_step, str) else None)
                    or "O banco solicitou uma confirmação adicional."
                )

                if action_links:
                    links_text = "\n".join(action_links)
                    message = f"{message}\nAcesse para autorizar: {links_text}"

                if parameter_form:
                    try:
                        logger.debug(
                            "WAITING_USER_INPUT parameter_form=%s insights=%s",
                            json.dumps(parameter_form, ensure_ascii=False),
                            json.dumps(connector_insights, ensure_ascii=False) if isinstance(connector_insights, dict) else connector_insights,
                        )
                    except Exception:
                        logger.debug("WAITING_USER_INPUT parameter_form could not be serialized")

                form_items = parameter_form.get('items') if isinstance(parameter_form, dict) else None
                if form_items:
                    raise BankConnectorAdditionalAuthRequired(
                        message,
                        detail,
                        item=item,
                        form=parameter_form,
                        next_step=next_step,
                        insights=connector_insights,
                    )

                raise BankConnectorUserActionRequired(message, detail, item=item)

            if status in {"LOGIN_ERROR", "INVALID_CREDENTIALS", "ERROR", "SUSPENDED"}:
                raise BankConnectorError(detail or "O banco rejeitou as credenciais informadas.")

            time.sleep(interval)

        raise BankConnectorTimeout("O banco ainda está processando sua autorização. Tente novamente em alguns minutos.")
    
    def list_accounts(self, user_id: int) -> List[Dict]:
        """Lista todas as contas bancárias de um usuário"""
        with engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT 
                        ba.id,
                        ba.account_id,
                        ba.account_type,
                        ba.account_number,
                        ba.account_name,
                        ba.balance,
                        ba.currency,
                        bc.connector_name
                    FROM bank_accounts ba
                    JOIN bank_connections bc ON ba.connection_id = bc.id
                    WHERE bc.user_id = :user_id
                    ORDER BY ba.created_at DESC
                """),
                {"user_id": user_id}
            )
            
            accounts = []
            for row in result:
                accounts.append({
                    'id': row[0],
                    'account_id': row[1],
                    'account_type': row[2],
                    'account_number': row[3],
                    'account_name': row[4],
                    'balance': float(row[5]) if row[5] else 0.0,
                    'currency': row[6],
                    'bank_name': row[7]
                })
            
            return accounts
    
    def get_total_balance(self, user_id: int) -> float:
        """Calcula saldo total consolidado de todas as contas"""
        with engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT COALESCE(SUM(ba.balance), 0) as total
                    FROM bank_accounts ba
                    JOIN bank_connections bc ON ba.connection_id = bc.id
                    WHERE bc.user_id = :user_id
                """),
                {"user_id": user_id}
            )
            
            row = result.fetchone()
            if row:
                return float(row[0])
            
            return 0.0
    
    # ==================== TRANSAÇÕES ====================
    
    def sync_transactions(self, connection_id: int, days: int = 30):
        """
        Sincroniza transações de todas as contas de uma conexão
        
        Args:
            connection_id: ID da conexão
            days: Quantos dias de histórico buscar
        """
        logger.info(f"💰 Sincronizando transações (últimos {days} dias)...")
        
        try:
            # Obter contas da conexão
            with engine.connect() as conn:
                result = conn.execute(
                    text("SELECT id, account_id FROM bank_accounts WHERE connection_id = :connection_id"),
                    {"connection_id": connection_id}
                )
                accounts = result.fetchall()
            
            from_date = datetime.now() - timedelta(days=days)
            total_transactions = 0
            
            with engine.connect() as conn:
                for account_row in accounts:
                    account_db_id, account_id = account_row
                    
                    # Buscar transações no Pluggy
                    transactions = self.client.list_transactions(
                        account_id=account_id,
                        from_date=from_date
                    )
                    
                    # Salvar no banco
                    for trans in transactions:
                        conn.execute(
                            text("""
                                INSERT INTO bank_transactions
                                    (account_id, transaction_id, description, amount, 
                                     date, type, category, merchant_name)
                                VALUES (:account_id, :transaction_id, :description, :amount,
                                        :date, :type, :category, :merchant_name)
                                ON CONFLICT (transaction_id) DO NOTHING
                            """),
                            {
                                "account_id": account_db_id,
                                "transaction_id": trans['id'],
                                "description": trans.get('description'),
                                "amount": trans.get('amount'),
                                "date": trans.get('date'),
                                "type": trans.get('type'),
                                "category": trans.get('category'),
                                "merchant_name": trans.get('merchantName')
                            }
                        )
                    
                    total_transactions += len(transactions)
                
                conn.commit()
            
            logger.info(f"✅ {total_transactions} transações sincronizadas")
            
        except Exception as e:
            logger.error(f"❌ Erro ao sincronizar transações: {e}")
            raise
    
    def list_transactions(
        self, 
        user_id: int, 
        limit: int = 50,
        days: int = 30
    ) -> List[Dict]:
        """Lista transações recentes de um usuário"""
        with engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT 
                        bt.description,
                        bt.amount,
                        bt.date,
                        bt.type,
                        bt.category,
                        bt.merchant_name,
                        ba.account_name,
                        bc.connector_name
                    FROM bank_transactions bt
                    JOIN bank_accounts ba ON bt.account_id = ba.id
                    JOIN bank_connections bc ON ba.connection_id = bc.id
                    WHERE bc.user_id = :user_id
                        AND bt.date >= CURRENT_DATE - INTERVAL ':days days'
                    ORDER BY bt.date DESC, bt.created_at DESC
                    LIMIT :limit
                """),
                {"user_id": user_id, "days": days, "limit": limit}
            )
            
            transactions = []
            for row in result:
                transactions.append({
                    'description': row[0],
                    'amount': float(row[1]) if row[1] else 0.0,
                    'date': row[2],
                    'type': row[3],
                    'category': row[4],
                    'merchant': row[5],
                    'account': row[6],
                    'bank': row[7]
                })
            
            return transactions

    def get_item_status(self, item_id: str) -> Dict:
        """Obtém status atual de um item direto do Pluggy."""
        try:
            return self.client.get_item(item_id)
        except Exception as exc:
            logger.error(f"❌ Erro ao consultar status do item {item_id}: {exc}")
            return {}

    def resume_connection(
        self,
        user_id: int,
        connector_id: int,
        item_id: str,
        login_credentials: Dict,
        additional_credentials: Dict,
    ) -> Dict:
        """Continua uma conexão aguardando dados extras (OTP, token, etc)."""

        logger.info(
            "🔁 Continuando conexão %s para usuário %s com credenciais adicionais",
            item_id,
            user_id,
        )

        credentials = dict(login_credentials or {})
        credentials.update(additional_credentials or {})

        try:
            self.client.update_item(item_id, credentials)
            final_item = self._wait_until_ready(item_id)
            status = final_item.get('status')
            status_detail = final_item.get('statusDetail')

            connector = self.client.get_connector(connector_id)
            connector_name = connector.get('name', 'Desconhecido')

            with engine.connect() as conn:
                result = conn.execute(
                    text(
                        """
                        INSERT INTO bank_connections
                            (user_id, item_id, connector_id, connector_name, status)
                        VALUES (:user_id, :item_id, :connector_id, :connector_name, :status)
                        ON CONFLICT (item_id) DO UPDATE SET
                            status = EXCLUDED.status,
                            updated_at = CURRENT_TIMESTAMP
                        RETURNING id, item_id, connector_name, status, created_at
                        """
                    ),
                    {
                        "user_id": user_id,
                        "item_id": item_id,
                        "connector_id": connector_id,
                        "connector_name": connector_name,
                        "status": status,
                    },
                )
                conn.commit()
                row = result.fetchone()

            if not row:
                raise Exception("Erro ao atualizar/registrar conexão após etapa adicional")

            connection_id = row[0]
            self._sync_accounts(connection_id, item_id)

            return {
                "id": row[0],
                "item_id": row[1],
                "connector_name": row[2],
                "status": row[3],
                "created_at": row[4],
                "status_detail": status_detail,
            }

        except Exception as exc:
            logger.error(f"❌ Erro ao continuar conexão {item_id}: {exc}")
            raise
