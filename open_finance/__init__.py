"""
🏦 Módulo Open Finance - Integração com API do Banco Central
Conecta com instituições financeiras via Pluggy para dados reais em tempo real
"""

__version__ = "1.0.0"
__author__ = "Maestro Financeiro Team"

from .pluggy_client import PluggyClient
from .bank_connector_module import BankConnector
from .data_sync import DataSynchronizer

__all__ = [
    'PluggyClient',
    'BankConnector', 
    'DataSynchronizer'
]
