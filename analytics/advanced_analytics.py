"""
🆕 ANALYTICS AVANÇADO - MaestroFin
Extensões avançadas para o sistema de analytics
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import logging

class AdvancedAnalytics:
    """Extensões avançadas para analytics"""
    
    def __init__(self, db_path: str = "analytics.db"):
        self.db_path = db_path
        self.init_advanced_tables()
    
    def init_advanced_tables(self):
        """Inicializa tabelas avançadas"""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                -- Tabela de funil de onboarding
                CREATE TABLE IF NOT EXISTS onboarding_funnel (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    username TEXT,
                    step_name TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    completed BOOLEAN DEFAULT TRUE,
                    metadata TEXT
                );
                
                -- Tabela de performance da IA
                CREATE TABLE IF NOT EXISTS ai_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    username TEXT,
                    operation_type TEXT NOT NULL,
                    success BOOLEAN NOT NULL,
                    response_time_ms INTEGER,
                    confidence_score REAL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT
                );
                
                -- Índices
                CREATE INDEX IF NOT EXISTS idx_onboarding_user_step 
                ON onboarding_funnel(user_id, step_name);
                
                CREATE INDEX IF NOT EXISTS idx_ai_performance_type_time 
                ON ai_performance(operation_type, timestamp);
            """)
    
    def track_onboarding_step(self, user_id: int, username: str, step_name: str, 
                             completed: bool = True, metadata: Dict = None):
        """Rastreia passos do funil de onboarding"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO onboarding_funnel (user_id, username, step_name, completed, metadata)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, username, step_name, completed, 
                 json.dumps(metadata) if metadata else None))
    
    def track_ai_performance(self, operation_type: str, success: bool, response_time_ms: int,
                           user_id: int = None, username: str = None, 
                           confidence_score: float = None, metadata: Dict = None):
        """Rastreia performance das operações de IA"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO ai_performance 
                (user_id, username, operation_type, success, response_time_ms, 
                 confidence_score, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, username, operation_type, success, response_time_ms,
                 confidence_score, json.dumps(metadata) if metadata else None))
    
    def get_onboarding_funnel(self, days_back: int = 30) -> Dict[str, Any]:
        """Retorna dados do funil de onboarding"""
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Passos do funil
            funnel_data = conn.execute("""
                SELECT 
                    step_name,
                    COUNT(DISTINCT user_id) as users_reached,
                    COUNT(DISTINCT CASE WHEN completed THEN user_id END) as users_completed
                FROM onboarding_funnel 
                WHERE timestamp >= ?
                GROUP BY step_name
                ORDER BY users_reached DESC
            """, (cutoff_date,)).fetchall()
            
            # Calcular taxa de completação
            result = []
            for row in funnel_data:
                completion_rate = (row['users_completed'] / row['users_reached'] * 100) if row['users_reached'] > 0 else 0
                result.append({
                    'step_name': row['step_name'],
                    'users_reached': row['users_reached'],
                    'users_completed': row['users_completed'],
                    'completion_rate': round(completion_rate, 2)
                })
            
            return {
                'period': f'{cutoff_date.date()} a {datetime.now().date()}',
                'funnel_steps': result
            }
    
    def get_ai_performance_summary(self, days_back: int = 7) -> Dict[str, Any]:
        """Retorna resumo de performance da IA"""
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Performance geral
            overall_stats = conn.execute("""
                SELECT 
                    COUNT(*) as total_operations,
                    COUNT(CASE WHEN success THEN 1 END) as successful_operations,
                    AVG(response_time_ms) as avg_response_time,
                    AVG(CASE WHEN confidence_score IS NOT NULL THEN confidence_score END) as avg_confidence
                FROM ai_performance 
                WHERE timestamp >= ?
            """, (cutoff_date,)).fetchone()
            
            # Performance por tipo
            by_type = conn.execute("""
                SELECT 
                    operation_type,
                    COUNT(*) as total_operations,
                    COUNT(CASE WHEN success THEN 1 END) as successful_operations,
                    AVG(response_time_ms) as avg_response_time
                FROM ai_performance 
                WHERE timestamp >= ?
                GROUP BY operation_type
            """, (cutoff_date,)).fetchall()
            
            # Calcular taxa de sucesso geral
            success_rate = 0
            if overall_stats['total_operations'] > 0:
                success_rate = overall_stats['successful_operations'] / overall_stats['total_operations'] * 100
            
            return {
                'period': f'{cutoff_date.date()} a {datetime.now().date()}',
                'overall': {
                    'total_operations': overall_stats['total_operations'] or 0,
                    'success_rate': round(success_rate, 2),
                    'avg_response_time': round(overall_stats['avg_response_time'] or 0, 2),
                    'avg_confidence': round(overall_stats['avg_confidence'] or 0, 3)
                },
                'by_type': [dict(row) for row in by_type]
            }

# Instância global
advanced_analytics = AdvancedAnalytics()
