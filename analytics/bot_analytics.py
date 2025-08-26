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
        logger.debug(f"📊 MOCK: {username} executou /{command} - {'OK' if success else 'ERRO'}")
    
    def track_daily_user(self, user_id: int, username: str, first_command: str = None):
        logger.debug(f"👤 MOCK: Usuário diário {username}")
    
    def track_error(self, user_id: int, username: str, error_type: str, error_message: str, command: str = None):
        logger.debug(f"❌ MOCK: Erro {error_type} para {username}")

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
    """Decorator de compatibilidade para tracking de comandos"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(update, context):
            user = update.effective_user
            cmd = command_name or getattr(func, '__name__', 'unknown')
            
            start_time = datetime.now()
            
            try:
                result = await func(update, context)
                
                # Calcular tempo de execução
                execution_time = (datetime.now() - start_time).total_seconds() * 1000
                
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
