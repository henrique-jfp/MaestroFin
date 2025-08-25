#!/usr/bin/env python3
"""
🔄 COMPATIBILITY LAYER - Fallback para bot_analytics.py
Este arquivo existe apenas para compatibilidade com imports antigos.
O sistema principal usa analytics.bot_analytics_postgresql
"""

import logging
from typing import Optional, Dict, Any, Callable
from functools import wraps
from datetime import datetime

logger = logging.getLogger(__name__)

class BotAnalytics:
    """
    Classe de compatibilidade para sistemas locais/antigos
    Em produção, usar analytics.bot_analytics_postgresql
    """
    
    def __init__(self):
        self.db_path = "analytics.db"
        logger.info("⚠️ Usando BotAnalytics de compatibilidade (SQLite mock)")
    
    def track_command_usage(self, user_id: int, username: str, command: str, 
                          success: bool = True, execution_time_ms: Optional[int] = None):
        """Track command usage - compatibilidade"""
        logger.debug(f"📊 MOCK: {username} executou /{command} - {'OK' if success else 'ERRO'}")
    
    def track_daily_user(self, user_id: int, username: str, first_command: str = None):
        """Track daily user - compatibilidade"""
        logger.debug(f"👤 MOCK: Usuário diário {username}")
    
    def log_error(self, error_type: str, error_message: str, user_id: int = None, 
                  username: str = None, command: str = None):
        """Log error - compatibilidade"""
        logger.error(f"❌ MOCK: {error_type}: {error_message}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get basic stats - mock data"""
        return {
            'total_users': 0,
            'total_commands': 0,
            'error_count': 0,
            'status': 'mock_compatibility_layer'
        }

# Instância global para compatibilidade
analytics = BotAnalytics()

def track_command(command_name: str):
    """
    Decorator para rastrear comandos - compatibilidade
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(update, context, *args, **kwargs):
            try:
                start_time = datetime.utcnow()
                result = await func(update, context, *args, **kwargs)
                
                # Track success (mock)
                user_id = update.effective_user.id
                username = update.effective_user.username or "N/A"
                
                execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                analytics.track_command_usage(
                    user_id=user_id,
                    username=username, 
                    command=command_name,
                    success=True,
                    execution_time_ms=execution_time
                )
                
                return result
                
            except Exception as e:
                # Track error (mock)
                user_id = update.effective_user.id if update.effective_user else None
                username = update.effective_user.username if update.effective_user else "N/A"
                
                analytics.log_error(
                    error_type=type(e).__name__,
                    error_message=str(e),
                    user_id=user_id,
                    username=username,
                    command=command_name
                )
                
                raise e
                
        return wrapper
    return decorator

logger.info("✅ Analytics de compatibilidade carregado (SQLite mock)")
