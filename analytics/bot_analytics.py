"""
Sistema de Analytics e Monitoramento - MaestroFin Bot
Coleta métricas detalhadas de uso, erros e performance
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging
import functools

class BotAnalytics:
    def __init__(self, db_path: str = "analytics.db"):
        self.db_path = db_path
        self.init_database()
        
    def init_database(self):
        """Inicializa tabelas de analytics"""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                -- Tabela de eventos de comandos
                CREATE TABLE IF NOT EXISTS command_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    username TEXT,
                    command TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    success BOOLEAN DEFAULT TRUE,
                    execution_time_ms INTEGER,
                    parameters TEXT -- JSON com parâmetros extras
                );
                
                -- Tabela de acessos diários únicos
                CREATE TABLE IF NOT EXISTS daily_users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    username TEXT,
                    date DATE NOT NULL,
                    first_command TEXT,
                    total_commands INTEGER DEFAULT 1,
                    UNIQUE(user_id, date)
                );
                
                -- Tabela de eventos de doação
                CREATE TABLE IF NOT EXISTS donation_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    username TEXT,
                    event_type TEXT NOT NULL, -- 'donation_message_shown', 'donation_clicked', 'donation_completed'
                    amount REAL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT -- JSON com dados extras
                );
                
                -- Tabela de logs de erros
                CREATE TABLE IF NOT EXISTS error_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    username TEXT,
                    command TEXT,
                    error_type TEXT NOT NULL,
                    error_message TEXT NOT NULL,
                    stack_trace TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT -- JSON com contexto adicional
                );
                
                -- Tabela de métricas de performance
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_name TEXT NOT NULL,
                    metric_value REAL NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT
                );
                
                -- Tabela de sessões de usuário
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    username TEXT,
                    session_start DATETIME DEFAULT CURRENT_TIMESTAMP,
                    session_end DATETIME,
                    commands_count INTEGER DEFAULT 0,
                    duration_minutes INTEGER
                );
                
                -- Índices para performance
                CREATE INDEX IF NOT EXISTS idx_command_usage_user_date 
                ON command_usage(user_id, DATE(timestamp));
                
                CREATE INDEX IF NOT EXISTS idx_daily_users_date 
                ON daily_users(date);
                
                CREATE INDEX IF NOT EXISTS idx_error_logs_timestamp 
                ON error_logs(timestamp);
            """)
    
    def track_command_usage(self, user_id: int, username: str, command: str, 
                           success: bool = True, execution_time_ms: int = 0,
                           parameters: Dict = None):
        """Registra uso de comando"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO command_usage (user_id, username, command, success, execution_time_ms, parameters)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, username, command, success, execution_time_ms, 
                 json.dumps(parameters) if parameters else None))
            
        # Atualizar usuário diário
        self._update_daily_user(user_id, username, command)
    
    def _update_daily_user(self, user_id: int, username: str, command: str):
        """Atualiza estatísticas de usuário diário"""
        today = datetime.now().date()
        
        with sqlite3.connect(self.db_path) as conn:
            # Tentar inserir novo usuário do dia
            conn.execute("""
                INSERT OR IGNORE INTO daily_users (user_id, username, date, first_command, total_commands)
                VALUES (?, ?, ?, ?, 1)
            """, (user_id, username, today, command))
            
            # Incrementar contagem de comandos
            conn.execute("""
                UPDATE daily_users 
                SET total_commands = total_commands + 1,
                    username = ?
                WHERE user_id = ? AND date = ?
            """, (username, user_id, today))
    
    def track_donation_event(self, user_id: int, username: str, event_type: str,
                            amount: float = None, metadata: Dict = None):
        """Registra eventos relacionados a doações"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO donation_events (user_id, username, event_type, amount, metadata)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, username, event_type, amount, 
                 json.dumps(metadata) if metadata else None))
    
    def log_error(self, error_type: str, error_message: str, stack_trace: str = None,
                  user_id: int = None, username: str = None, command: str = None,
                  metadata: Dict = None):
        """Registra erro no sistema"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO error_logs (user_id, username, command, error_type, 
                                       error_message, stack_trace, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, username, command, error_type, error_message, 
                 stack_trace, json.dumps(metadata) if metadata else None))
    
    def get_daily_stats(self, date: str = None) -> Dict[str, Any]:
        """Retorna estatísticas do dia"""
        if not date:
            date = datetime.now().date()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Usuários únicos
            unique_users = conn.execute("""
                SELECT COUNT(*) as count FROM daily_users WHERE date = ?
            """, (date,)).fetchone()['count']
            
            # Total de comandos
            total_commands = conn.execute("""
                SELECT COUNT(*) as count FROM command_usage WHERE DATE(timestamp) = ?
            """, (date,)).fetchone()['count']
            
            # Comandos mais usados
            top_commands = conn.execute("""
                SELECT command, COUNT(*) as count
                FROM command_usage 
                WHERE DATE(timestamp) = ?
                GROUP BY command 
                ORDER BY count DESC 
                LIMIT 10
            """, (date,)).fetchall()
            
            # Erros do dia
            errors_count = conn.execute("""
                SELECT COUNT(*) as count FROM error_logs WHERE DATE(timestamp) = ?
            """, (date,)).fetchone()['count']
            
            return {
                'date': str(date),
                'unique_users': unique_users,
                'total_commands': total_commands,
                'top_commands': [dict(row) for row in top_commands],
                'errors_count': errors_count
            }
    
    def get_weekly_stats(self, weeks_back: int = 0) -> Dict[str, Any]:
        """Retorna estatísticas da semana"""
        end_date = datetime.now().date() - timedelta(weeks=weeks_back)
        start_date = end_date - timedelta(days=6)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Usuários únicos da semana
            unique_users = conn.execute("""
                SELECT COUNT(DISTINCT user_id) as count 
                FROM daily_users 
                WHERE date BETWEEN ? AND ?
            """, (start_date, end_date)).fetchone()['count']
            
            # Total de comandos
            total_commands = conn.execute("""
                SELECT COUNT(*) as count 
                FROM command_usage 
                WHERE DATE(timestamp) BETWEEN ? AND ?
            """, (start_date, end_date)).fetchone()['count']
            
            # Crescimento por dia
            daily_growth = conn.execute("""
                SELECT date, COUNT(*) as users
                FROM daily_users 
                WHERE date BETWEEN ? AND ?
                GROUP BY date
                ORDER BY date
            """, (start_date, end_date)).fetchall()
            
            return {
                'period': f"{start_date} a {end_date}",
                'unique_users': unique_users,
                'total_commands': total_commands,
                'daily_growth': [dict(row) for row in daily_growth]
            }
    
    def get_donation_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas de doações"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Mensagens de doação mostradas
            donations_shown = conn.execute("""
                SELECT COUNT(*) as count 
                FROM donation_events 
                WHERE event_type = 'donation_message_shown'
            """).fetchone()['count']
            
            # Cliques em doação
            donations_clicked = conn.execute("""
                SELECT COUNT(*) as count 
                FROM donation_events 
                WHERE event_type = 'donation_clicked'
            """).fetchone()['count']
            
            # Doações completadas
            donations_completed = conn.execute("""
                SELECT COUNT(*) as count, SUM(amount) as total_amount
                FROM donation_events 
                WHERE event_type = 'donation_completed'
            """).fetchone()
            
            # Taxa de conversão
            conversion_rate = 0
            if donations_shown > 0:
                conversion_rate = (donations_completed['count'] / donations_shown) * 100
            
            return {
                'donations_shown': donations_shown,
                'donations_clicked': donations_clicked,
                'donations_completed': donations_completed['count'],
                'total_amount': donations_completed['total_amount'] or 0,
                'conversion_rate': round(conversion_rate, 2)
            }
    
    def get_error_summary(self, days_back: int = 7) -> Dict[str, Any]:
        """Retorna resumo de erros"""
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Erros por tipo
            errors_by_type = conn.execute("""
                SELECT error_type, COUNT(*) as count
                FROM error_logs 
                WHERE timestamp >= ?
                GROUP BY error_type
                ORDER BY count DESC
            """, (cutoff_date,)).fetchall()
            
            # Erros recentes
            recent_errors = conn.execute("""
                SELECT error_type, error_message, command, timestamp, username
                FROM error_logs 
                WHERE timestamp >= ?
                ORDER BY timestamp DESC
                LIMIT 20
            """, (cutoff_date,)).fetchall()
            
            return {
                'period_days': days_back,
                'errors_by_type': [dict(row) for row in errors_by_type],
                'recent_errors': [dict(row) for row in recent_errors]
            }

# Singleton para uso global
analytics = BotAnalytics()

def track_command(command_name: str):
    """Decorator para rastrear uso de comandos automaticamente"""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(update, context):
            user_id = update.effective_user.id
            username = update.effective_user.username or update.effective_user.first_name
            start_time = datetime.now()
            
            try:
                result = await func(update, context)
                
                # Calcular tempo de execução
                execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
                
                # Registrar sucesso
                analytics.track_command_usage(
                    user_id=user_id,
                    username=username,
                    command=command_name,
                    success=True,
                    execution_time_ms=execution_time
                )
                
                return result
                
            except Exception as e:
                # Calcular tempo até erro
                execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
                
                # Registrar erro na analytics
                analytics.track_command_usage(
                    user_id=user_id,
                    username=username,
                    command=command_name,
                    success=False,
                    execution_time_ms=execution_time
                )
                
                # Log detalhado do erro
                analytics.log_error(
                    error_type=type(e).__name__,
                    error_message=str(e),
                    stack_trace=str(e.__traceback__),
                    user_id=user_id,
                    username=username,
                    command=command_name
                )
                
                # Re-raise para manter comportamento original
                raise
                
        return wrapper
    return decorator
