"""
open_finance/pluggy_client.py

Módulo cliente para a API da Pluggy.
Responsabilidade Única: Encapsular toda a comunicação HTTP com a API da Pluggy,
gerenciando autenticação, requisições e tratamento de erros de API.
Este módulo é agnóstico ao Telegram e ao nosso banco de dados.
"""
import os
import logging
import time
from typing import Dict, List, Optional
from datetime import datetime, timedelta

import requests
from requests import Response
import json # Adicionado para o decode de erro

# Configurações
PLUGGY_CLIENT_ID = os.getenv("PLUGGY_CLIENT_ID")
PLUGGY_CLIENT_SECRET = os.getenv("PLUGGY_CLIENT_SECRET")
PLUGGY_BASE_URL = "https://api.pluggy.ai"

logger = logging.getLogger(__name__)

# Cache em memória para a API Key
_api_key_cache: Dict[str, any] = {"key": None, "expires_at": None}


class PluggyClientError(Exception):
    """Exceção base para erros do cliente Pluggy."""
    def __init__(self, message: str, status_code: Optional[int] = None, details: Optional[Dict] = None):
        super().__init__(message)
        self.status_code = status_code
        self.details = details or {}

class PluggyClient:
    """Um cliente HTTP para a API da Pluggy."""

    def __init__(self, timeout: int = 45):
        self.timeout = timeout
        self.api_key = self._get_api_key()

    def _get_api_key(self) -> str:
        """Obtém uma API Key da Pluggy, utilizando um cache de 23 horas."""
        now = datetime.now()
        if _api_key_cache.get("key") and _api_key_cache.get("expires_at", now) > now:
            return _api_key_cache["key"]

        logger.info("🔑 Obtendo nova API Key da Pluggy...")
        if not PLUGGY_CLIENT_ID or not PLUGGY_CLIENT_SECRET:
            raise PluggyClientError("PLUGGY_CLIENT_ID e PLUGGY_CLIENT_SECRET devem ser configurados.")

        try:
            response = requests.post(
                f"{PLUGGY_BASE_URL}/auth",
                json={"clientId": PLUGGY_CLIENT_ID, "clientSecret": PLUGGY_CLIENT_SECRET},
                headers={"Content-Type": "application/json"},
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()
            
            _api_key_cache["key"] = data["apiKey"]
            _api_key_cache["expires_at"] = now + timedelta(hours=23)
            
            logger.info("✅ API Key da Pluggy obtida e cacheada com sucesso.")
            return data["apiKey"]
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Erro de rede ao obter API Key da Pluggy: {e}")
            raise PluggyClientError(f"Erro de rede ao autenticar com a Pluggy: {e}")

    def _request(self, method: str, endpoint: str, **kwargs) -> Response:
        """Executa uma requisição autenticada para a API da Pluggy."""
        url = f"{PLUGGY_BASE_URL}{endpoint}"
        headers = {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json",
            **kwargs.pop("headers", {})
        }

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                timeout=self.timeout,
                **kwargs
            )
            response.raise_for_status()
            return response
        except requests.exceptions.HTTPError as e:
            details = {}
            try:
                details = e.response.json()
            except json.JSONDecodeError:
                details = {"raw_response": e.response.text}
            
            logger.error(f"❌ Erro HTTP {e.response.status_code} em {method} {endpoint}: {details}")
            raise PluggyClientError(
                f"Erro na API Pluggy: {details.get('message', e.response.reason)}",
                status_code=e.response.status_code,
                details=details
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Erro de rede em {method} {endpoint}: {e}")
            raise PluggyClientError(f"Erro de rede ao comunicar com a Pluggy: {e}")

    # --- MÉTODOS DE SERVIÇO ---

    def get_connectors(self) -> List[Dict]:
        """Busca a lista de conectores (bancos) disponíveis no Brasil."""
        logger.info("Buscando conectores da Pluggy...")
        response = self._request("GET", "/connectors", params={"countries": "BR", "pageSize": 500})
        return response.json().get("results", [])

    def create_item(self, connector_id: int, parameters: Dict) -> Dict:
        """Cria um novo 'item' (conexão) para um conector específico."""
        logger.info(f"Criando item para o conector {connector_id}...")
        payload = {"connectorId": connector_id, "parameters": parameters}
        response = self._request("POST", "/items", json=payload)
        return response.json()

    def get_item(self, item_id: str) -> Dict:
        """Busca os detalhes e o status de um 'item'."""
        logger.debug(f"Buscando detalhes do item {item_id}...")
        response = self._request("GET", f"/items/{item_id}")
        return response.json()

    def delete_item(self, item_id: str) -> None:
        """Deleta um 'item' (conexão)."""
        logger.info(f"Deletando item {item_id}...")
        self._request("DELETE", f"/items/{item_id}")
        logger.info(f"Item {item_id} deletado com sucesso.")

    def list_accounts(self, item_id: str) -> List[Dict]:
        """Lista todas as contas associadas a um 'item'."""
        logger.info(f"Listando contas para o item {item_id}...")
        response = self._request("GET", "/accounts", params={"itemId": item_id, "pageSize": 500})
        return response.json().get("results", [])

    def get_credit_card(self, account_id: str) -> Dict:
        """Busca os detalhes específicos de um cartão de crédito."""
        logger.info(f"Buscando detalhes do cartão de crédito {account_id}...")
        response = self._request("GET", f"/accounts/{account_id}/credit-card")
        return response.json()

    def list_transactions(self, account_id: str, from_date: str) -> List[Dict]:
        """Lista as transações de uma conta a partir de uma data."""
        logger.info(f"Listando transações da conta {account_id} a partir de {from_date}...")
        params = {"accountId": account_id, "from": from_date, "pageSize": 500}
        response = self._request("GET", "/transactions", params=params)
        return response.json().get("results", [])
