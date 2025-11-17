"""
🔗 Gerenciador de Conexões Bancárias
Gerencia conexões de usuários com instituições financeiras
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime
from database.database import SessionLocal, engine  # Import correto
from sqlalchemy import text
from .pluggy_client import PluggyClient

logger = logging.getLogger(__name__)


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
                FOREIGN KEY (user_id) REFERENCES usuarios(user_id) ON DELETE CASCADE
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
            
            # Obter nome do conector
            connector = self.client.get_connector(connector_id)
            connector_name = connector.get('name', 'Desconhecido')
            
            # Salvar no banco
            query = """
                INSERT INTO bank_connections 
                    (user_id, item_id, connector_id, connector_name, status)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, item_id, connector_name, status, created_at
            """
            
            result = self.db.execute_query(
                query,
                (user_id, item['id'], connector_id, connector_name, item.get('status')),
                fetch=True
            )
            
            if result:
                connection_data = result[0]
                logger.info(f"✅ Conexão criada: {connection_data[1]}")
                
                # Sincronizar contas imediatamente
                self._sync_accounts(connection_data[0], item['id'])
                
                return {
                    'id': connection_data[0],
                    'item_id': connection_data[1],
                    'connector_name': connection_data[2],
                    'status': connection_data[3],
                    'created_at': connection_data[4]
                }
            
            raise Exception("Erro ao salvar conexão no banco")
            
        except Exception as e:
            logger.error(f"❌ Erro ao criar conexão: {e}")
            raise
    
    def list_connections(self, user_id: int) -> List[Dict]:
        """Lista todas as conexões bancárias de um usuário"""
        query = """
            SELECT id, item_id, connector_name, status, created_at, last_sync_at
            FROM bank_connections
            WHERE user_id = %s
            ORDER BY created_at DESC
        """
        
        results = self.db.execute_query(query, (user_id,), fetch=True)
        
        connections = []
        for row in results:
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
        query = """
            SELECT id, user_id, item_id, connector_name, status, created_at, last_sync_at
            FROM bank_connections
            WHERE id = %s
        """
        
        result = self.db.execute_query(query, (connection_id,), fetch=True)
        
        if result:
            row = result[0]
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
            query = "DELETE FROM bank_connections WHERE id = %s"
            self.db.execute_query(query, (connection_id,))
            
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
            
            for account in accounts:
                query = """
                    INSERT INTO bank_accounts 
                        (connection_id, account_id, account_type, account_number, 
                         account_name, balance, currency)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (account_id) 
                    DO UPDATE SET
                        balance = EXCLUDED.balance,
                        updated_at = CURRENT_TIMESTAMP
                """
                
                self.db.execute_query(
                    query,
                    (
                        connection_id,
                        account['id'],
                        account.get('type'),
                        account.get('number'),
                        account.get('name'),
                        account.get('balance'),
                        account.get('currencyCode', 'BRL')
                    )
                )
            
            # Atualizar timestamp de sincronização
            update_query = """
                UPDATE bank_connections 
                SET last_sync_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """
            self.db.execute_query(update_query, (connection_id,))
            
            logger.info(f"✅ {len(accounts)} contas sincronizadas")
            
        except Exception as e:
            logger.error(f"❌ Erro ao sincronizar contas: {e}")
            raise
    
    def list_accounts(self, user_id: int) -> List[Dict]:
        """Lista todas as contas bancárias de um usuário"""
        query = """
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
            WHERE bc.user_id = %s
            ORDER BY ba.created_at DESC
        """
        
        results = self.db.execute_query(query, (user_id,), fetch=True)
        
        accounts = []
        for row in results:
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
        query = """
            SELECT COALESCE(SUM(ba.balance), 0) as total
            FROM bank_accounts ba
            JOIN bank_connections bc ON ba.connection_id = bc.id
            WHERE bc.user_id = %s
        """
        
        result = self.db.execute_query(query, (user_id,), fetch=True)
        
        if result:
            return float(result[0][0])
        
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
            query = "SELECT id, account_id FROM bank_accounts WHERE connection_id = %s"
            accounts = self.db.execute_query(query, (connection_id,), fetch=True)
            
            from_date = datetime.now() - timedelta(days=days)
            total_transactions = 0
            
            for account_row in accounts:
                account_db_id, account_id = account_row
                
                # Buscar transações no Pluggy
                transactions = self.client.list_transactions(
                    account_id=account_id,
                    from_date=from_date
                )
                
                # Salvar no banco
                for trans in transactions:
                    insert_query = """
                        INSERT INTO bank_transactions
                            (account_id, transaction_id, description, amount, 
                             date, type, category, merchant_name)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (transaction_id) DO NOTHING
                    """
                    
                    self.db.execute_query(
                        insert_query,
                        (
                            account_db_id,
                            trans['id'],
                            trans.get('description'),
                            trans.get('amount'),
                            trans.get('date'),
                            trans.get('type'),
                            trans.get('category'),
                            trans.get('merchantName')
                        )
                    )
                
                total_transactions += len(transactions)
            
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
        query = """
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
            WHERE bc.user_id = %s
                AND bt.date >= CURRENT_DATE - INTERVAL '%s days'
            ORDER BY bt.date DESC, bt.created_at DESC
            LIMIT %s
        """
        
        results = self.db.execute_query(query, (user_id, days, limit), fetch=True)
        
        transactions = []
        for row in results:
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
