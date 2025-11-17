"""
🔌 Cliente Pluggy API - Open Finance
Cliente HTTP para comunicação com API Pluggy
Documentação: https://docs.pluggy.ai
"""

import os
import logging
import requests
from typing import Dict, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class PluggyClient:
    """Cliente para API Pluggy - Open Finance"""
    
    BASE_URL = "https://api.pluggy.ai"
    
    def __init__(self, client_id: Optional[str] = None, client_secret: Optional[str] = None):
        """
        Inicializa cliente Pluggy
        
        Args:
            client_id: Client ID do Pluggy (ou variável PLUGGY_CLIENT_ID)
            client_secret: Client Secret (ou variável PLUGGY_CLIENT_SECRET)
        """
        self.client_id = client_id or os.getenv('PLUGGY_CLIENT_ID')
        self.client_secret = client_secret or os.getenv('PLUGGY_CLIENT_SECRET')
        
        if not self.client_id or not self.client_secret:
            raise ValueError(
                "❌ Credenciais Pluggy não encontradas! "
                "Configure PLUGGY_CLIENT_ID e PLUGGY_CLIENT_SECRET"
            )
        
        self._api_key = None
        self._api_key_expires_at = None
        
        logger.info("✅ Cliente Pluggy inicializado")
    
    def _get_api_key(self) -> str:
        """Obtém API Key (com cache)"""
        now = datetime.now()
        
        # Se já tem key válida, retornar
        if self._api_key and self._api_key_expires_at and now < self._api_key_expires_at:
            return self._api_key
        
        # Gerar nova API Key
        logger.info("🔑 Gerando nova API Key...")
        
        url = f"{self.BASE_URL}/auth"
        
        payload = {
            "clientId": self.client_id,
            "clientSecret": self.client_secret,
        }
        headers = {"Content-Type": "application/json"}

        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        self._api_key = data['apiKey']
        
        # API Key expira em 24h
        self._api_key_expires_at = now + timedelta(hours=24)
        
        logger.info("✅ API Key obtida com sucesso")
        return self._api_key
    
    def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        Faz requisição HTTP para API Pluggy
        
        Args:
            method: GET, POST, PATCH, DELETE
            endpoint: Endpoint da API (ex: /items)
            data: Dados JSON para POST/PATCH
            params: Query parameters
            
        Returns:
            Resposta JSON da API
        """
        api_key = self._get_api_key()
        
        url = f"{self.BASE_URL}{endpoint}"
        headers = {
            "X-API-KEY": api_key,
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=data,
                params=params,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"❌ Erro HTTP {response.status_code}: {e}")
            logger.error(f"Response: {response.text}")
            raise
        except Exception as e:
            logger.error(f"❌ Erro ao fazer requisição: {e}")
            raise
    
    # ==================== CONNECTORS ====================
    
    def list_connectors(self, country: str = "BR") -> List[Dict]:
        """
        Lista instituições financeiras disponíveis
        
        Args:
            country: Código do país (BR, MX, AR, etc)
            
        Returns:
            Lista de conectores disponíveis
        """
        logger.info(f"📋 Listando conectores do país: {country}")
        
        params = {"countries": country}
        result = self._make_request("GET", "/connectors", params=params)
        
        connectors = result.get('results', [])
        logger.info(f"✅ {len(connectors)} conectores encontrados")
        
        return connectors
    
    def get_connector(self, connector_id: int) -> Dict:
        """Obtém detalhes de um conector específico"""
        return self._make_request("GET", f"/connectors/{connector_id}")
    
    # ==================== ITEMS (Conexões) ====================
    
    def create_item(self, connector_id: int, credentials: Dict) -> Dict:
        """
        Cria conexão com instituição financeira (Item)
        
        Args:
            connector_id: ID do conector (banco)
            credentials: Credenciais de login
                Ex: {"username": "cpf", "password": "senha"}
                
        Returns:
            Item criado com status da conexão
        """
        logger.info(f"🔗 Criando conexão com conector {connector_id}...")
        
        data = {
            "connectorId": connector_id,
            "parameters": credentials
        }
        
        item = self._make_request("POST", "/items", data=data)
        logger.info(f"✅ Item criado: {item.get('id')}")
        
        return item
    
    def get_item(self, item_id: str) -> Dict:
        """Obtém detalhes de uma conexão (Item)"""
        return self._make_request("GET", f"/items/{item_id}")
    
    def update_item(self, item_id: str, credentials: Dict) -> Dict:
        """Atualiza credenciais de uma conexão"""
        logger.info(f"🔄 Atualizando item {item_id}...")
        
        data = {"parameters": credentials}
        return self._make_request("PATCH", f"/items/{item_id}", data=data)
    
    def delete_item(self, item_id: str) -> bool:
        """Remove conexão com banco"""
        logger.info(f"🗑️ Removendo item {item_id}...")
        
        try:
            self._make_request("DELETE", f"/items/{item_id}")
            logger.info("✅ Item removido com sucesso")
            return True
        except Exception as e:
            logger.error(f"❌ Erro ao remover item: {e}")
            return False
    
    # ==================== ACCOUNTS (Contas) ====================
    
    def list_accounts(self, item_id: str) -> List[Dict]:
        """
        Lista contas bancárias de uma conexão
        
        Args:
            item_id: ID da conexão (Item)
            
        Returns:
            Lista de contas (corrente, poupança, cartão)
        """
        logger.info(f"💳 Listando contas do item {item_id}...")
        
        result = self._make_request("GET", f"/accounts?itemId={item_id}")
        
        accounts = result.get('results', [])
        logger.info(f"✅ {len(accounts)} contas encontradas")
        
        return accounts
    
    def get_account(self, account_id: str) -> Dict:
        """Obtém detalhes de uma conta específica"""
        return self._make_request("GET", f"/accounts/{account_id}")
    
    # ==================== TRANSACTIONS (Transações) ====================
    
    def list_transactions(
        self, 
        account_id: str,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        page_size: int = 100
    ) -> List[Dict]:
        """
        Lista transações de uma conta
        
        Args:
            account_id: ID da conta
            from_date: Data inicial (default: 30 dias atrás)
            to_date: Data final (default: hoje)
            page_size: Itens por página
            
        Returns:
            Lista de transações
        """
        if not from_date:
            from_date = datetime.now() - timedelta(days=30)
        if not to_date:
            to_date = datetime.now()
        
        logger.info(
            f"💰 Listando transações de {from_date.date()} a {to_date.date()}..."
        )
        
        params = {
            "accountId": account_id,
            "from": from_date.strftime("%Y-%m-%d"),
            "to": to_date.strftime("%Y-%m-%d"),
            "pageSize": page_size
        }
        
        result = self._make_request("GET", "/transactions", params=params)
        
        transactions = result.get('results', [])
        logger.info(f"✅ {len(transactions)} transações encontradas")
        
        return transactions
    
    # ==================== INVESTMENTS (Investimentos) ====================
    
    def list_investments(self, item_id: str) -> List[Dict]:
        """
        Lista investimentos de uma conexão
        
        Args:
            item_id: ID da conexão
            
        Returns:
            Lista de investimentos (CDB, LCI, ações, etc)
        """
        logger.info(f"📈 Listando investimentos do item {item_id}...")
        
        result = self._make_request("GET", f"/investments?itemId={item_id}")
        
        investments = result.get('results', [])
        logger.info(f"✅ {len(investments)} investimentos encontrados")
        
        return investments
    
    # ==================== IDENTITY (Dados pessoais) ====================
    
    def get_identity(self, item_id: str) -> Dict:
        """
        Obtém dados pessoais do usuário
        
        Args:
            item_id: ID da conexão
            
        Returns:
            Nome, CPF, email, telefone, endereço
        """
        logger.info(f"👤 Obtendo dados de identidade do item {item_id}...")
        
        result = self._make_request("GET", f"/identity?itemId={item_id}")
        
        identity = result.get('results', [{}])[0] if result.get('results') else {}
        return identity
    
    # ==================== WEBHOOKS ====================
    
    def create_webhook(self, url: str, event: str) -> Dict:
        """
        Cria webhook para receber notificações
        
        Args:
            url: URL que receberá POST requests
            event: Tipo de evento (item/*, accounts/*, transactions/*)
            
        Returns:
            Webhook criado
        """
        logger.info(f"🔔 Criando webhook para evento {event}...")
        
        data = {
            "event": event,
            "url": url
        }
        
        return self._make_request("POST", "/webhooks", data=data)
    
    def list_webhooks(self) -> List[Dict]:
        """Lista webhooks configurados"""
        result = self._make_request("GET", "/webhooks")
        return result.get('results', [])


# ==================== HELPER FUNCTIONS ====================

def format_currency(value: float) -> str:
    """Formata valor monetário"""
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def format_account_type(account_type: str) -> str:
    """Traduz tipo de conta"""
    types = {
        "BANK": "🏦 Conta Corrente",
        "CREDIT": "💳 Cartão de Crédito",
        "SAVINGS": "🐷 Poupança",
        "INVESTMENT": "📈 Investimentos"
    }
    return types.get(account_type, account_type)
