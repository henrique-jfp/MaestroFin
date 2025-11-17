"""
💾 Gerenciamento de Tokens em Banco de Dados
Salva, recupera e atualiza tokens de forma segura (criptografado)
"""

import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_

from models import UserBankToken, Usuario
from open_finance.token_encryption import get_encryption

logger = logging.getLogger(__name__)


class TokenDatabaseManager:
    """Gerencia persistência de tokens no banco de dados"""
    
    def __init__(self, db_session: Session):
        """
        Args:
            db_session: Sessão SQLAlchemy
        """
        self.db = db_session
        self.encryption = get_encryption()
    
    def _get_usuario_id(self, telegram_user_id: int) -> int | None:
        """
        Converte telegram_user_id para id de usuário na BD
        
        Args:
            telegram_user_id: ID do Telegram (grande número)
            
        Returns:
            ID do usuário na BD ou None
        """
        try:
            usuario = self.db.query(Usuario).filter(
                Usuario.telegram_id == telegram_user_id
            ).first()
            
            if usuario:
                return usuario.id
            
            logger.warning(f"⚠️ Usuário com telegram_id {telegram_user_id} não encontrado")
            return None
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar usuário: {e}")
            return None
    
    def save_token(self, telegram_user_id: int, bank: str, token: str, token_type: str) -> bool:
        """
        Salva token de banco no BD (criptografado)
        
        Args:
            telegram_user_id: ID do Telegram do usuário
            bank: Nome do banco ('inter', 'itau', etc)
            token: Token em plain text
            token_type: Tipo de token ('isafe', 'itoken', 'bearer', etc)
            
        Returns:
            True se salvo com sucesso
        """
        try:
            # Converter telegram_user_id para usuario.id
            usuario_id = self._get_usuario_id(telegram_user_id)
            if not usuario_id:
                logger.error(f"❌ Não foi possível encontrar usuário com telegram_id {telegram_user_id}")
                return False
            
            # Verifica se já existe token para este banco
            existing = self.db.query(UserBankToken).filter(
                and_(
                    UserBankToken.id_usuario == usuario_id,
                    UserBankToken.banco == bank.lower()
                )
            ).first()
            
            # Encripta o token
            encrypted_token = self.encryption.encrypt(token)
            
            if existing:
                # Atualiza token existente
                existing.encrypted_token = encrypted_token
                existing.token_type = token_type
                existing.conectado_em = datetime.now(timezone.utc)
                existing.ativo = True
                logger.info(f"🔄 Token {bank} atualizado para usuário {telegram_user_id}")
            else:
                # Cria novo registro
                new_token = UserBankToken(
                    id_usuario=usuario_id,
                    banco=bank.lower(),
                    encrypted_token=encrypted_token,
                    token_type=token_type,
                    ativo=True
                )
                self.db.add(new_token)
                logger.info(f"✅ Token {bank} salvo para usuário {telegram_user_id}")
            
            self.db.commit()
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao salvar token no BD: {e}")
            self.db.rollback()
            raise
    
    def get_token(self, telegram_user_id: int, bank: str) -> dict | None:
        """
        Recupera token do BD (decriptografado)
        
        Args:
            telegram_user_id: ID do Telegram do usuário
            bank: Nome do banco
            
        Returns:
            Dict com {token, token_type, conectado_em} ou None
        """
        try:
            # Converter telegram_user_id para usuario.id
            usuario_id = self._get_usuario_id(telegram_user_id)
            if not usuario_id:
                return None
            
            token_record = self.db.query(UserBankToken).filter(
                and_(
                    UserBankToken.id_usuario == usuario_id,
                    UserBankToken.banco == bank.lower(),
                    UserBankToken.ativo == True
                )
            ).first()
            
            if not token_record:
                logger.warning(f"⚠️  Token {bank} não encontrado para usuário {telegram_user_id}")
                return None
            
            # Atualiza último acesso
            token_record.ultimo_acesso = datetime.now(timezone.utc)
            self.db.commit()
            
            # Decripta o token
            decrypted_token = self.encryption.decrypt(token_record.encrypted_token)
            
            return {
                'token': decrypted_token,
                'token_type': token_record.token_type,
                'conectado_em': token_record.conectado_em,
                'ultimo_acesso': token_record.ultimo_acesso
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao recuperar token do BD: {e}")
            raise
    
    def get_all_tokens(self, telegram_user_id: int) -> list[dict]:
        """
        Recupera todos os tokens ativos de um usuário
        
        Args:
            telegram_user_id: ID do Telegram do usuário
            
        Returns:
            Lista de dicts com informações dos tokens
        """
        try:
            # Converter telegram_user_id para usuario.id
            usuario_id = self._get_usuario_id(telegram_user_id)
            if not usuario_id:
                return []
            
            tokens = self.db.query(UserBankToken).filter(
                and_(
                    UserBankToken.id_usuario == usuario_id,
                    UserBankToken.ativo == True
                )
            ).all()
            
            result = []
            for token_record in tokens:
                result.append({
                    'banco': token_record.banco,
                    'token_type': token_record.token_type,
                    'conectado_em': token_record.conectado_em,
                    'ultimo_acesso': token_record.ultimo_acesso
                })
            
            logger.info(f"📋 {len(result)} token(s) recuperado(s) para usuário {telegram_user_id}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Erro ao recuperar tokens do BD: {e}")
            raise
    
    def delete_token(self, telegram_user_id: int, bank: str) -> bool:
        """
        Deleta (marca como inativo) um token
        
        Args:
            telegram_user_id: ID do Telegram do usuário
            bank: Nome do banco
            
        Returns:
            True se deletado
        """
        try:
            # Converter telegram_user_id para usuario.id
            usuario_id = self._get_usuario_id(telegram_user_id)
            if not usuario_id:
                return False
            
            token_record = self.db.query(UserBankToken).filter(
                and_(
                    UserBankToken.id_usuario == usuario_id,
                    UserBankToken.banco == bank.lower()
                )
            ).first()
            
            if token_record:
                token_record.ativo = False
                self.db.commit()
                logger.info(f"🗑️  Token {bank} deletado para usuário {telegram_user_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Erro ao deletar token: {e}")
            self.db.rollback()
            raise
    
    def has_active_token(self, telegram_user_id: int, bank: str) -> bool:
        """
        Verifica se usuário tem token ativo para um banco
        
        Args:
            telegram_user_id: ID do Telegram do usuário
            bank: Nome do banco
            
        Returns:
            True se tem token ativo
        """
        try:
            # Converter telegram_user_id para usuario.id
            usuario_id = self._get_usuario_id(telegram_user_id)
            if not usuario_id:
                return False
            
            exists = self.db.query(UserBankToken).filter(
                and_(
                    UserBankToken.id_usuario == usuario_id,
                    UserBankToken.banco == bank.lower(),
                    UserBankToken.ativo == True
                )
            ).first() is not None
            
            return exists
            
        except Exception as e:
            logger.error(f"❌ Erro ao verificar token: {e}")
            return False
