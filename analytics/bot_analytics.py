#!/usr/bin/env python3
"""
🔄 COMPATIBILITY LAYER - bot_analytics.py
Arquivo de compatibilidade para evitar quebrar imports existentes.
Redireciona para a versão PostgreSQL quando disponível.
"""

import logging
import os
from typing import Optional, Dict, Any, Callable
from functools import wraps
from datetime import datetime

logger = logging.getLogger(__name__)

# Tentar usar a versão PostgreSQL quando disponível
_analytics_instance = None
_track_function = None

def _initialize_analytics():
    """Inicializa o sistema de analytics"""
    global _analytics_instance, _track_function
    
    if _analytics_instance is not None:
        return
    
    try:
        # Se estiver no Render, usar PostgreSQL
        if os.environ.get('DATABASE_URL'):
            from analytics.bot_analytics_postgresql import get_analytics
            _analytics_instance = get_analytics()
            logger.info("✅ Analytics PostgreSQL carregado via compatibilidade")
        else:
            # Modo local - criar mock básico
            _analytics_instance = MockAnalytics()
            logger.info("⚠️ Usando BotAnalytics de compatibilidade (SQLite mock)")
    except Exception as e:
        logger.warning(f"⚠️ Erro ao carregar analytics: {e}, usando mock")
        _analytics_instance = MockAnalytics()

class MockAnalytics:
    """Analytics mock para compatibilidade local"""
    
    def track_command_usage(self, user_id: int, username: str, command: str, 
                          success: bool = True, execution_time_ms: Optional[int] = None):
        # Log mais detalhado para debugging
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        logger.debug(f"📊 [ANALYTICS-DEBUG] MOCK: {timestamp} | {username} (ID:{user_id}) | /{command} | {'✅' if success else '❌'} | {execution_time_ms}ms")
    
    def track_daily_user(self, user_id: int, username: str, first_command: str = None):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        logger.debug(f"👤 [ANALYTICS-DEBUG] MOCK: {timestamp} | Usuário diário {username} (ID:{user_id})")
    
    def track_error(self, user_id: int, username: str, error_type: str, error_message: str, command: str = None):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        logger.debug(f"❌ [ANALYTICS-DEBUG] MOCK: {timestamp} | Erro {error_type} para {username} | Cmd: {command} | Msg: {error_message[:100]}")
        
    def log_error(self, user_id: int, username: str, command: str, error_type: str, 
                  error_message: str, stack_trace: str = None):
        """Método adicional para compatibilidade com logs de erro"""
        self.track_error(user_id, username, error_type, error_message, command)

class BotAnalytics:
    """Classe de compatibilidade para analytics"""
    
    def __init__(self):
        _initialize_analytics()
    
    def track_command_usage(self, user_id: int, username: str, command: str, 
                          success: bool = True, execution_time_ms: Optional[int] = None):
        _initialize_analytics()
        return _analytics_instance.track_command_usage(user_id, username, command, success, execution_time_ms)
    
    def track_daily_user(self, user_id: int, username: str, first_command: str = None):
        _initialize_analytics()
        return _analytics_instance.track_daily_user(user_id, username, first_command)
    
    def track_error(self, user_id: int, username: str, error_type: str, error_message: str, command: str = None):
        _initialize_analytics()
        return _analytics_instance.track_error(user_id, username, error_type, error_message, command)

def track_command(command_name: str = None):
    """Decorator de compatibilidade para tracking de comandos com logs detalhados"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(update, context):
            user = update.effective_user
            cmd = command_name or getattr(func, '__name__', 'unknown')
            
            # Log detalhado do início do comando
            start_timestamp = datetime.now()
            logger.info(f"🎯 [ANALYTICS-DEBUG] Iniciando comando /{cmd} | User: {user.username or f'user_{user.id}'} | Timestamp: {start_timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
            
            try:
                result = await func(update, context)
                
                # Calcular tempo de execução
                end_timestamp = datetime.now()
                execution_time = (end_timestamp - start_timestamp).total_seconds() * 1000
                
                # Log de sucesso
                logger.info(f"✅ [ANALYTICS-DEBUG] Comando /{cmd} executado com SUCESSO em {execution_time:.0f}ms")
                
                # Track success
                _initialize_analytics()
                _analytics_instance.track_command_usage(
                    user.id, 
                    user.username or f"user_{user.id}", 
                    cmd, 
                    True, 
                    int(execution_time)
                )
                
                return result
                
            except Exception as e:
                # Calcular tempo de execução mesmo em caso de erro
                end_timestamp = datetime.now()
                execution_time = (end_timestamp - start_timestamp).total_seconds() * 1000
                
                # Log de erro detalhado
                logger.error(f"❌ [ANALYTICS-DEBUG] Comando /{cmd} FALHOU em {execution_time:.0f}ms | Erro: {type(e).__name__}: {str(e)[:100]}")
                
                # Track error
                _initialize_analytics()
                _analytics_instance.track_command_usage(
                    user.id, 
                    user.username or f"user_{user.id}", 
                    cmd, 
                    False, 
                    int(execution_time)
                )
                
                # Também registrar o erro específico se método existir
                if hasattr(_analytics_instance, 'track_error'):
                    _analytics_instance.track_error(
                        user.id,
                        user.username or f"user_{user.id}",
                        type(e).__name__,
                        str(e),
                        cmd
                    )
                
                raise  # Re-raise para não mascarar o erro
                # Track error
                _initialize_analytics()
                _analytics_instance.track_error(
                    user.id,
                    user.username or f"user_{user.id}",
                    type(e).__name__,
                    str(e),
                    cmd
                )
                raise
        
        return wrapper
    return decorator

def get_analytics():
    """Retorna instância global de analytics"""
    _initialize_analytics()
    return _analytics_instance

# Instância global para compatibilidade
analytics = BotAnalytics()

logger.info("📦 Bot Analytics Compatibility Layer carregado")
