"""
🔐 Criptografia de Tokens - Proteção de Dados Sensíveis
Encripta/decripta tokens de banco antes de armazenar em BD
"""

import os
import logging
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


class TokenEncryption:
    """Gerencia criptografia e descriptografia de tokens"""
    
    def __init__(self):
        """Inicializa com chave de criptografia do ambiente"""
        self.encryption_key = os.getenv('TOKEN_ENCRYPTION_KEY')
        
        if not self.encryption_key:
            logger.warning("⚠️  TOKEN_ENCRYPTION_KEY não definida - gerando nova chave")
            self.encryption_key = Fernet.generate_key().decode()
            logger.warning(f"Adicione isso ao .env: TOKEN_ENCRYPTION_KEY={self.encryption_key}")
        
        try:
            self.cipher = Fernet(self.encryption_key.encode() if isinstance(self.encryption_key, str) else self.encryption_key)
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar criptografia: {e}")
            raise
    
    def encrypt(self, token: str) -> str:
        """
        Encripta um token
        
        Args:
            token: Token em plain text
            
        Returns:
            Token criptografado (string base64)
        """
        try:
            if not isinstance(token, bytes):
                token = token.encode()
            
            encrypted = self.cipher.encrypt(token)
            return encrypted.decode()
        except Exception as e:
            logger.error(f"❌ Erro ao encriptar token: {e}")
            raise
    
    def decrypt(self, encrypted_token: str) -> str:
        """
        Decripta um token
        
        Args:
            encrypted_token: Token criptografado (string base64)
            
        Returns:
            Token em plain text
        """
        try:
            if not isinstance(encrypted_token, bytes):
                encrypted_token = encrypted_token.encode()
            
            decrypted = self.cipher.decrypt(encrypted_token)
            return decrypted.decode()
        except Exception as e:
            logger.error(f"❌ Erro ao decriptar token: {e}")
            raise
    
    @staticmethod
    def generate_new_key() -> str:
        """Gera uma nova chave de criptografia"""
        return Fernet.generate_key().decode()


# Singleton para usar em toda a app
_encryption_instance = None


def get_encryption() -> TokenEncryption:
    """Factory function para obter a instância de criptografia"""
    global _encryption_instance
    if _encryption_instance is None:
        _encryption_instance = TokenEncryption()
    return _encryption_instance
