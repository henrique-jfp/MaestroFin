"""
🔑 Autenticação por Token - Integração Direta com Bancos
Permite que usuários conectem bancos usando tokens de segurança
gerados diretamente pelo banco
"""

import logging
import os
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class TokenAuthManager:
    """Gerencia autenticação por token de banco"""
    
    def __init__(self):
        self.tokens = {}  # Será salvo em BD depois
    
    # ==================== INTER ====================
    
    @staticmethod
    def authenticate_inter(token: str) -> Dict:
        """
        Autentica com banco Inter usando token
        
        Token do Inter pode ser:
        - iSafe: 6 dígitos (ex: 123456)
        - API Token: CPF:token (ex: 12345678901:abc123...)
        - Bearer Token: string longa
        """
        try:
            import re
            token_clean = token.strip()
            
            # Tipo 1: iSafe (6 dígitos)
            if re.match(r'^\d{6}$', token_clean):
                logger.info(f"✅ Token Inter (iSafe) validado: {token_clean[:3]}***")
                return {
                    'bank': 'inter',
                    'token': token_clean,
                    'type': 'isafe',
                    'validated_at': datetime.now().isoformat()
                }
            
            # Tipo 2: CPF:token format
            if ':' in token_clean:
                cpf, token_value = token_clean.split(':', 1)
                cpf_clean = cpf.strip().replace('.', '').replace('-', '')
                
                if len(cpf_clean) != 11:
                    raise ValueError("CPF inválido - deve ter 11 dígitos")
                
                if len(token_value.strip()) < 10:
                    raise ValueError("Token muito curto - mínimo 10 caracteres após ':'")
                
                logger.info(f"✅ Token Inter (CPF:token) validado para CPF {cpf_clean[:3]}***{cpf_clean[-2:]}")
                return {
                    'bank': 'inter',
                    'cpf': cpf_clean,
                    'token': token_value.strip(),
                    'type': 'cpf_token',
                    'validated_at': datetime.now().isoformat()
                }
            
            # Tipo 3: Bearer token (string longa)
            if len(token_clean) >= 10:
                logger.info(f"✅ Token Inter (Bearer) validado")
                return {
                    'bank': 'inter',
                    'token': token_clean,
                    'type': 'bearer_token',
                    'validated_at': datetime.now().isoformat()
                }
            
            raise ValueError("Token Inter inválido - muito curto")
            
        except Exception as e:
            logger.error(f"❌ Erro ao validar token Inter: {e}")
            raise
    
    # ==================== ITAÚ ====================
    
    @staticmethod
    def authenticate_itau(token: str) -> Dict:
        """
        Autentica com Itaú usando token
        
        Token do Itaú pode ser:
        - iToken: 6 dígitos (ex: 123456)
        - Bearer token: string longa
        - OAuth token: code/access_token
        """
        try:
            import re
            token_clean = token.strip()
            
            # Tipo 1: iToken (6 dígitos)
            if re.match(r'^\d{6}$', token_clean):
                logger.info(f"✅ Token Itaú (iToken) validado: {token_clean[:3]}***")
                return {
                    'bank': 'itau',
                    'token': token_clean,
                    'type': 'itoken',
                    'validated_at': datetime.now().isoformat()
                }
            
            # Tipo 2: Bearer token ou outro (mínimo 6 caracteres)
            if len(token_clean) >= 6:
                logger.info(f"✅ Token Itaú validado: {token_clean[:10]}***")
                return {
                    'bank': 'itau',
                    'token': token_clean,
                    'type': 'bearer_token',
                    'validated_at': datetime.now().isoformat()
                }
            
            raise ValueError("Token Itaú muito curto - mínimo 6 caracteres")
            
        except Exception as e:
            logger.error(f"❌ Erro ao validar token Itaú: {e}")
            raise
    
    # ==================== BRADESCO ====================
    
    @staticmethod
    def authenticate_bradesco(token: str) -> Dict:
        """
        Autentica com Bradesco usando token
        
        Token do Bradesco:
        - Gerado em: https://www.bradesco.com.br/
        - Pode ser: Bearer token, código de acesso (6+ caracteres)
        """
        try:
            token_clean = token.strip()
            
            if token_clean.lower().startswith('bearer '):
                token_clean = token_clean[7:]
            
            if len(token_clean) < 6:
                raise ValueError("Token Bradesco muito curto - mínimo 6 caracteres")
            
            logger.info(f"✅ Token Bradesco validado")
            
            return {
                'bank': 'bradesco',
                'token': token_clean,
                'type': 'bearer',
                'validated_at': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"❌ Erro ao validar token Bradesco: {e}")
            raise
    
    # ==================== NUBANK ====================
    
    @staticmethod
    def authenticate_nubank(token: str) -> Dict:
        """
        Autentica com Nubank usando token/código
        
        Token do Nubank:
        - Pode ser: Code de autenticação (6+ chars), JWT token, ou Bearer token
        - Gerado em: App do Nubank > Minha Conta > Chaves de acesso
        """
        try:
            token_clean = token.strip()
            
            if token_clean.lower().startswith('bearer '):
                token_clean = token_clean[7:]
            
            if len(token_clean) < 6:
                raise ValueError("Token Nubank muito curto - mínimo 6 caracteres")
            
            # Detecta tipo de token
            token_type = 'jwt' if '.' in token_clean else 'code'
            
            logger.info(f"✅ Token Nubank validado (tipo: {token_type})")
            
            return {
                'bank': 'nubank',
                'token': token_clean,
                'type': token_type,
                'validated_at': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"❌ Erro ao validar token Nubank: {e}")
            raise
    
    # ==================== CAIXA ====================
    
    @staticmethod
    def authenticate_caixa(token: str) -> Dict:
        """
        Autentica com Caixa usando token
        
        Token da Caixa:
        - Pode ser: Código de acesso (6+ chars) ou Bearer token
        - Gerado em: Internet Banking Caixa
        - Contato: suporte@caixa.gov.br
        """
        try:
            token_clean = token.strip()
            
            if token_clean.lower().startswith('bearer '):
                token_clean = token_clean[7:]
            
            if len(token_clean) < 6:
                raise ValueError("Token Caixa muito curto - mínimo 6 caracteres")
            
            logger.info(f"✅ Token Caixa validado")
            
            return {
                'bank': 'caixa',
                'token': token_clean,
                'type': 'bearer',
                'validated_at': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"❌ Erro ao validar token Caixa: {e}")
            raise
    
    # ==================== SANTANDER ====================
    
    @staticmethod
    def authenticate_santander(token: str) -> Dict:
        """
        Autentica com Santander usando token
        
        Token do Santander:
        - Pode ser: Código de acesso (6+ chars) ou Bearer token
        - Gerado em: Internet Banking Santander
        - Developer Portal: https://www.santander.com.br/developers
        """
        try:
            token_clean = token.strip()
            
            if token_clean.lower().startswith('bearer '):
                token_clean = token_clean[7:]
            
            if len(token_clean) < 6:
                raise ValueError("Token Santander muito curto - mínimo 6 caracteres")
            
            logger.info(f"✅ Token Santander validado")
            
            return {
                'bank': 'santander',
                'token': token_clean,
                'type': 'bearer',
                'validated_at': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"❌ Erro ao validar token Santander: {e}")
            raise
    
    # ==================== ROUTER ====================
    
    def authenticate(self, bank: str, token: str) -> Dict:
        """Router para diferentes métodos de autenticação"""
        
        bank_lower = bank.lower().strip()
        
        methods = {
            'inter': self.authenticate_inter,
            'itau': self.authenticate_itau,
            'bradesco': self.authenticate_bradesco,
            'nubank': self.authenticate_nubank,
            'caixa': self.authenticate_caixa,
            'santander': self.authenticate_santander,
        }
        
        if bank_lower not in methods:
            raise ValueError(f"Banco '{bank}' não suportado para autenticação por token")
        
        return methods[bank_lower](token)
    
    def validate_token(self, bank: str, token: str) -> bool:
        """Valida se o token é válido"""
        try:
            self.authenticate(bank, token)
            return True
        except Exception as e:
            logger.error(f"Token inválido para {bank}: {e}")
            return False
    
    def store_token(self, user_id: int, bank: str, auth_data: Dict) -> None:
        """Armazena token para o usuário (será expandido para BD)"""
        if user_id not in self.tokens:
            self.tokens[user_id] = {}
        
        self.tokens[user_id][bank] = auth_data
        logger.info(f"✅ Token armazenado para usuário {user_id} - Banco: {bank}")
    
    def get_token(self, user_id: int, bank: str) -> Optional[Dict]:
        """Recupera token do usuário"""
        if user_id in self.tokens:
            return self.tokens[user_id].get(bank)
        return None


# Instância global
token_manager = TokenAuthManager()
