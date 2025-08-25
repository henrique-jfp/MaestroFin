"""
🚀 Analytics PostgreSQL - Versão para Render
Sistema de analytics que usa o PostgreSQL em vez de SQLite
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import os
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.sql import func

import functools

# Base para modelos SQLAlchemy
Base = declarative_base()

class CommandUsage(Base):
    __tablename__ = 'analytics_command_usage'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    username = Column(String(255))
    command = Column(String(255), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    success = Column(Boolean, default=True)
    execution_time_ms = Column(Integer)
    parameters = Column(Text)  # JSON

class DailyUsers(Base):
    __tablename__ = 'analytics_daily_users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    username = Column(String(255))
    date = Column(DateTime, nullable=False)
    first_command = Column(String(255))
    total_commands = Column(Integer, default=1)

class ErrorLogs(Base):
    __tablename__ = 'analytics_error_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer)
    username = Column(String(255))
    command = Column(String(255))
    error_type = Column(String(255), nullable=False)
    error_message = Column(Text, nullable=False)
    stack_trace = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
    extra_data = Column(Text)  # JSON - renomeado de 'metadata'

class BotAnalyticsPostgreSQL:
    def __init__(self):
        """Inicializa analytics com PostgreSQL"""
        self.db_url = os.getenv('DATABASE_URL')
        if not self.db_url:
            logging.error("❌ DATABASE_URL não configurado para analytics")
            return
            
        try:
            # Configurar engine PostgreSQL com SSL fix
            if self.db_url.startswith('postgres://'):
                self.db_url = self.db_url.replace('postgres://', 'postgresql://', 1)
            
            # 🔧 ULTRA ROBUST SSL FIX para Render PostgreSQL
            ssl_args = {
                'pool_pre_ping': True,
                'pool_recycle': 1800,  # Renovar conexões a cada 30 min
                'pool_size': 2,         # Pool menor mas mais estável
                'max_overflow': 1,      # Menos overflow para evitar SSL race conditions
                'pool_timeout': 20,     # Timeout razoável
                'echo': False           # Sem logs verbosos
            }
            
            if 'render' in self.db_url.lower() or 'amazonaws' in self.db_url.lower():
                ssl_args['connect_args'] = {
                    'sslmode': 'require',
                    'sslcert': None,
                    'sslkey': None,
                    'sslrootcert': None,
                    'connect_timeout': 10,
                    'application_name': 'maestrofin_analytics'
                }
                logging.info("🔐 Configurando SSL Ultra Robusto para PostgreSQL em produção")
            
            self.engine = create_engine(
                self.db_url, 
                **ssl_args
            )
            self.Session = sessionmaker(bind=self.engine)
            
            # Criar tabelas
            Base.metadata.create_all(self.engine)
            logging.info("✅ Analytics PostgreSQL inicializado")
            
        except Exception as e:
            logging.error(f"❌ Erro ao inicializar Analytics PostgreSQL: {e}")
            self.engine = None
            self.Session = None
    
    def track_command_usage(self, user_id: int, username: str, command: str, 
                           success: bool = True, execution_time_ms: int = 0,
                           parameters: Dict = None):
        """Registra uso de comando com retry automático"""
        if not self.Session:
            return
            
        max_retries = 3
        for attempt in range(max_retries):
            try:
                with self.Session() as session:
                    usage = CommandUsage(
                        user_id=user_id,
                        username=username,
                        command=command,
                        success=success,
                        execution_time_ms=execution_time_ms,
                        parameters=json.dumps(parameters) if parameters else None
                    )
                    session.add(usage)
                    session.commit()
                    
                    # Atualizar usuários diários
                    self._update_daily_user(session, user_id, username, command)
                    return  # Sucesso, sair do loop
                    
            except Exception as e:
                logging.error(f"❌ Erro ao registrar comando (tentativa {attempt + 1}): {e}")
                if attempt == max_retries - 1:
                    # Última tentativa, log detalhado
                    logging.error(f"💥 Falha definitiva ao registrar comando após {max_retries} tentativas")
                else:
                    # Aguarda antes da próxima tentativa
                    import time
                    time.sleep(0.5 * (attempt + 1))  # Backoff progressivo
    
    def _update_daily_user(self, session: Session, user_id: int, username: str, command: str):
        """Atualiza estatísticas de usuário diário"""
        try:
            today = datetime.now().date()
            
            # Buscar usuário do dia
            daily_user = session.query(DailyUsers).filter(
                DailyUsers.user_id == user_id,
                func.date(DailyUsers.date) == today
            ).first()
            
            if daily_user:
                # Incrementar comandos
                daily_user.total_commands += 1
                daily_user.username = username
            else:
                # Criar novo usuário do dia
                daily_user = DailyUsers(
                    user_id=user_id,
                    username=username,
                    date=datetime.now(),
                    first_command=command,
                    total_commands=1
                )
                session.add(daily_user)
            
            session.commit()
            
        except Exception as e:
            logging.error(f"❌ Erro ao atualizar usuário diário: {e}")
    
    def log_error(self, error_type: str, error_message: str, stack_trace: str = None,
                  user_id: int = None, username: str = None, command: str = None,
                  metadata: Dict = None):
        """Registra erro no sistema com retry automático"""
        if not self.Session:
            return
            
        max_retries = 2  # Menos tentativas para erros
        for attempt in range(max_retries):
            try:
                with self.Session() as session:
                    error_log = ErrorLogs(
                        user_id=user_id,
                        username=username,
                        command=command,
                        error_type=error_type,
                        error_message=error_message,
                        stack_trace=stack_trace,
                        extra_data=json.dumps(metadata) if metadata else None
                    )
                    session.add(error_log)
                    session.commit()
                    return  # Sucesso
                    
            except Exception as e:
                logging.error(f"❌ Erro ao registrar erro (tentativa {attempt + 1}): {e}")
                if attempt == max_retries - 1:
                    logging.error(f"💥 Falha ao registrar erro após {max_retries} tentativas")
                else:
                    import time
                    time.sleep(0.3)
    
    def get_daily_stats(self, date: str = None) -> Dict[str, Any]:
        """Retorna estatísticas do dia"""
        if not self.Session:
            return {'error': 'Analytics não disponível'}
            
        if not date:
            date = datetime.now().date()
        
        try:
            with self.Session() as session:
                # Usuários únicos
                unique_users = session.query(DailyUsers).filter(
                    func.date(DailyUsers.date) == date
                ).count()
                
                # Total de comandos
                total_commands = session.query(CommandUsage).filter(
                    func.date(CommandUsage.timestamp) == date
                ).count()
                
                # Comandos mais usados
                top_commands = session.query(
                    CommandUsage.command,
                    func.count(CommandUsage.id).label('count')
                ).filter(
                    func.date(CommandUsage.timestamp) == date
                ).group_by(CommandUsage.command).order_by(
                    func.count(CommandUsage.id).desc()
                ).limit(10).all()
                
                # Erros do dia
                errors_count = session.query(ErrorLogs).filter(
                    func.date(ErrorLogs.timestamp) == date
                ).count()
                
                # Taxa de sucesso
                success_count = session.query(CommandUsage).filter(
                    func.date(CommandUsage.timestamp) == date,
                    CommandUsage.success == True
                ).count()
                
                success_rate = 0
                if total_commands > 0:
                    success_rate = (success_count / total_commands) * 100
                
                # Tempo médio de execução
                avg_time = session.query(
                    func.avg(CommandUsage.execution_time_ms)
                ).filter(
                    func.date(CommandUsage.timestamp) == date,
                    CommandUsage.execution_time_ms > 0
                ).scalar() or 0
                
                return {
                    'date': str(date),
                    'unique_users': unique_users,
                    'total_commands': total_commands,
                    'top_commands': [{'command': cmd, 'count': count} for cmd, count in top_commands],
                    'errors_count': errors_count,
                    'success_rate': round(success_rate, 1),
                    'avg_execution_time': round(float(avg_time), 0) if avg_time else 0
                }
                
        except Exception as e:
            logging.error(f"❌ Erro ao obter estatísticas diárias: {e}")
            return {'error': str(e)}
    
    def get_weekly_stats(self, weeks_back: int = 0) -> Dict[str, Any]:
        """Retorna estatísticas da semana"""
        if not self.Session:
            return {'error': 'Analytics não disponível'}
            
        try:
            end_date = datetime.now().date() - timedelta(weeks=weeks_back * 7)
            start_date = end_date - timedelta(days=6)
            
            with self.Session() as session:
                # Usuários únicos da semana
                unique_users = session.query(func.count(func.distinct(DailyUsers.user_id))).filter(
                    func.date(DailyUsers.date) >= start_date,
                    func.date(DailyUsers.date) <= end_date
                ).scalar() or 0
                
                # Total de comandos
                total_commands = session.query(CommandUsage).filter(
                    func.date(CommandUsage.timestamp) >= start_date,
                    func.date(CommandUsage.timestamp) <= end_date
                ).count()
                
                return {
                    'period': f"{start_date} a {end_date}",
                    'unique_users': unique_users,
                    'total_commands': total_commands
                }
                
        except Exception as e:
            logging.error(f"❌ Erro ao obter estatísticas semanais: {e}")
            return {'error': str(e)}

# Singleton global para uso no sistema
analytics_pg = None

def get_analytics():
    """Retorna instância singleton do analytics"""
    global analytics_pg
    if analytics_pg is None:
        analytics_pg = BotAnalyticsPostgreSQL()
    return analytics_pg

# Para compatibilidade com código existente
analytics = get_analytics()

def get_session():
    """Retorna uma nova sessão SQLAlchemy para uso em endpoints Flask"""
    pg = get_analytics()
    if pg and pg.Session:
        return pg.Session()
    return None

def track_command(command_name: str):
    """
    Decorator para rastrear o uso de comandos de forma assíncrona,
    compatível com a infraestrutura do PostgreSQL.
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(update, context, *args, **kwargs):
            # Obter a instância correta do analytics
            pg_analytics = get_analytics()
            
            user = update.effective_user
            user_id = user.id if user else None
            username = user.username if user else 'N/A'
            
            start_time = datetime.utcnow()
            
            try:
                # Executa a função de handler original
                result = await func(update, context, *args, **kwargs)
                
                execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                
                # Registrar sucesso
                pg_analytics.track_command_usage(
                    user_id=user_id,
                    username=username,
                    command=command_name,
                    success=True,
                    execution_time_ms=execution_time
                )
                return result
                
            except Exception as e:
                execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                
                # Registrar falha
                pg_analytics.track_command_usage(
                    user_id=user_id,
                    username=username,
                    command=command_name,
                    success=False,
                    execution_time_ms=execution_time
                )
                
                # Log detalhado do erro
                import traceback
                pg_analytics.log_error(
                    error_type=type(e).__name__,
                    error_message=str(e),
                    stack_trace=traceback.format_exc(),
                    user_id=user_id,
                    username=username,
                    command=command_name
                )
                
                # Re-lança a exceção para que o bot possa tratá-la (ex: enviar msg de erro)
                raise

        return wrapper
    return decorator
