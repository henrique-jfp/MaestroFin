#!/usr/bin/env python3
"""
⚙️ CONFIGURAÇÃO AVANÇADA - MaestroFin
Sistema de configuração centralizada com validação e valores padrão
"""

import os
import logging
from typing import Any, Optional, Dict
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class DatabaseConfig:
    """Configurações de banco de dados"""
    url: str
    pool_size: int = 10
    max_overflow: int = 5
    pool_timeout: int = 30
    pool_recycle: int = 1800
    echo: bool = False

@dataclass
class CacheConfig:
    """Configurações de cache"""
    default_ttl: int = 300
    max_size: int = 1000
    enabled: bool = True

@dataclass
class AnalyticsConfig:
    """Configurações de analytics"""
    enabled: bool = True
    batch_size: int = 100
    flush_interval: int = 60
    retention_days: int = 90

@dataclass
class DashboardConfig:
    """Configurações do dashboard"""
    host: str = '0.0.0.0'
    port: int = 5000
    debug: bool = False
    threaded: bool = True
    auto_reload: bool = False

class ConfigManager:
    """Gerenciador de configurações"""
    
    def __init__(self):
        self._load_config()
    
    def _load_config(self):
        """Carrega configurações do ambiente"""
        # Database
        self.database = DatabaseConfig(
            url=os.getenv('DATABASE_URL', ''),
            pool_size=int(os.getenv('DB_POOL_SIZE', '10')),
            max_overflow=int(os.getenv('DB_MAX_OVERFLOW', '5')),
            pool_timeout=int(os.getenv('DB_POOL_TIMEOUT', '30')),
            pool_recycle=int(os.getenv('DB_POOL_RECYCLE', '1800')),
            echo=os.getenv('DB_ECHO', 'false').lower() == 'true'
        )
        
        # Cache
        self.cache = CacheConfig(
            default_ttl=int(os.getenv('CACHE_DEFAULT_TTL', '300')),
            max_size=int(os.getenv('CACHE_MAX_SIZE', '1000')),
            enabled=os.getenv('CACHE_ENABLED', 'true').lower() == 'true'
        )
        
        # Analytics
        self.analytics = AnalyticsConfig(
            enabled=os.getenv('ANALYTICS_ENABLED', 'true').lower() == 'true',
            batch_size=int(os.getenv('ANALYTICS_BATCH_SIZE', '100')),
            flush_interval=int(os.getenv('ANALYTICS_FLUSH_INTERVAL', '60')),
            retention_days=int(os.getenv('ANALYTICS_RETENTION_DAYS', '90'))
        )
        
        # Dashboard
        self.dashboard = DashboardConfig(
            host=os.getenv('DASHBOARD_HOST', '0.0.0.0'),
            port=int(os.getenv('PORT', '5000')),
            debug=self._is_debug_mode(),
            threaded=os.getenv('DASHBOARD_THREADED', 'true').lower() == 'true',
            auto_reload=os.getenv('DASHBOARD_AUTO_RELOAD', 'false').lower() == 'true'
        )
        
        # Telegram
        self.telegram_token = os.getenv('TELEGRAM_TOKEN')
        self.gemini_api_key = os.getenv('GEMINI_API_KEY')
        
        # Database URL for validation
        self.database_url = os.getenv('DATABASE_URL')
        
        # Environment
        self.environment = 'production' if self._is_production() else 'development'
        self.debug = self._is_debug_mode()
        self.is_production = self._is_production()
        self.is_render = bool(os.getenv('RENDER_SERVICE_NAME'))
        
        logger.info("✅ Configurações carregadas com sucesso")
        self.validate_config()
    
    def _is_debug_mode(self) -> bool:
        """Determina se deve usar modo debug"""
        if self._is_production():
            return False
        return os.getenv('DEBUG', 'false').lower() == 'true'
    
    def _is_production(self) -> bool:
        """Verifica se está em ambiente de produção"""
        return bool(
            os.getenv('RENDER_SERVICE_NAME') or 
            os.getenv('RAILWAY_ENVIRONMENT') or 
            os.getenv('PRODUCTION')
        )
    
    def validate_config(self):
        """Valida se as configurações essenciais estão presentes"""
        errors = []
        warnings = []
        
        # Verificações críticas apenas para produção
        if self.environment == 'production':
            if not self.telegram_token:
                errors.append("TELEGRAM_TOKEN não configurado")
            if not self.gemini_api_key:
                errors.append("GEMINI_API_KEY não configurado")
        else:
            # Em desenvolvimento, apenas avisos
            if not self.telegram_token:
                warnings.append("TELEGRAM_TOKEN não configurado (desenvolvimento)")
            if not self.gemini_api_key:
                warnings.append("GEMINI_API_KEY não configurado (desenvolvimento)")
        
        # Verificar configurações de banco
        if not self.database_url and self.environment == 'production':
            errors.append("DATABASE_URL não configurado")
            
        if errors:
            error_msg = f"Configuração inválida: {', '.join(errors)}"
            if self.environment == 'production':
                raise ValueError(error_msg)
            else:
                print(f"⚠️  {error_msg}")
        
        if warnings:
            for warning in warnings:
                print(f"⚠️  {warning}")
        
        return len(errors) == 0
    
    def get_database_config(self) -> Dict[str, Any]:
        """Retorna configuração do banco de dados para SQLAlchemy"""
        config = {
            'pool_size': self.database.pool_size,
            'max_overflow': self.database.max_overflow,
            'pool_timeout': self.database.pool_timeout,
            'pool_recycle': self.database.pool_recycle,
            'echo': self.database.echo
        }
        
        if self.is_render and self.database.url:
            # Configurações específicas para Render PostgreSQL
            config['connect_args'] = {
                'sslmode': 'require',
                'connect_timeout': 10,
                'application_name': 'maestrofin_app'
            }
        
        return config
    
    def get_flask_config(self) -> Dict[str, Any]:
        """Retorna configuração para Flask"""
        return {
            'host': self.dashboard.host,
            'port': self.dashboard.port,
            'debug': self.dashboard.debug,
            'threaded': self.dashboard.threaded,
            'use_reloader': self.dashboard.auto_reload
        }
    
    def print_config_summary(self):
        """Imprime resumo das configurações"""
        print("\n" + "="*60)
        print("⚙️  CONFIGURAÇÃO DO MAESTROFIN")
        print("="*60)
        print(f"🌍 Ambiente: {'Produção' if self.is_production else 'Desenvolvimento'}")
        print(f"🔧 Debug: {'Ativado' if self.dashboard.debug else 'Desativado'}")
        print(f"🗄️  Database: {'PostgreSQL' if self.database.url else 'SQLite/Mock'}")
        print(f"📊 Analytics: {'Ativado' if self.analytics.enabled else 'Desativado'}")
        print(f"💾 Cache: {'Ativado' if self.cache.enabled else 'Desativado'}")
        print(f"🌐 Dashboard: {self.dashboard.host}:{self.dashboard.port}")
        if self.is_render:
            print("☁️  Deploy: Render")
        print("="*60)

# Instância global
config = ConfigManager()

def get_config() -> ConfigManager:
    """Retorna instância global da configuração"""
    return config
