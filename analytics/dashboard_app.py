#!/usr/bin/env python3
"""
Dashboard Web para Analytics do MaestroFin Bot
Interface web limpa para visualizar métricas e estatísticas
"""

import os
import sys
import logging
from flask import Flask, render_template, jsonify, request
from datetime import datetime, timedelta

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configurar paths
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
template_dir = os.path.join(parent_dir, 'templates')
static_dir = os.path.join(parent_dir, 'static')
sys.path.insert(0, parent_dir)

# Criar app Flask
app = Flask(__name__, 
           template_folder=template_dir,
           static_folder=static_dir)

# Configurar analytics
analytics_available = False
is_render = bool(os.getenv('DATABASE_URL'))

if is_render:
    try:
        from analytics.bot_analytics_postgresql import get_analytics
        analytics = get_analytics()
        analytics_available = True
        logger.info("✅ Analytics PostgreSQL conectado")
    except ImportError as e:
        logger.warning(f"Analytics indisponível: {e}")
else:
    logger.info("Modo local - usando dados mock")

# --- CONFIGURAÇÃO E UTILITÁRIOS ---

def get_fallback_data():
    """Retorna dados padrão para fallback"""
    return {
        'total_users': 15,
        'total_commands': 127,
        'avg_response_time': 245.8,
        'error_count': 3,
        'status': 'fallback',
        'timestamp': datetime.now().isoformat()
    }

def execute_with_retry(func, max_retries=3):
    """Executa função com retry automático"""
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            logger.error(f"Tentativa {attempt + 1} falhou: {e}")
            if attempt == max_retries - 1:
                raise
    return None

# --- ROTAS PRINCIPAIS ---

@app.route('/')
def dashboard():
    """Página principal do dashboard"""
    try:
        return render_template('dashboard_analytics_clean.html')
    except Exception as e:
        return f"""
        <h1>ERRO NO DASHBOARD</h1>
        <p>Erro: {str(e)}</p>
        <p>Template: {os.path.exists(os.path.join(template_dir, 'dashboard_analytics_clean.html'))}</p>
        """

@app.route('/api/status')
def api_status():
    """Status da API"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'analytics_enabled': analytics_available,
        'environment': 'render' if is_render else 'local'
    })

# --- APIs DE DADOS ---

@app.route('/api/realtime')
def realtime_stats():
    """Métricas em tempo real com retry automático"""
    if not analytics_available:
        return jsonify(get_fallback_data())
    
    def get_real_data():
        from analytics.bot_analytics_postgresql import get_session
        from sqlalchemy import text
        
        session = get_session()
        if not session:
            raise Exception("Sessão não criada")
        
        try:
            cutoff = datetime.now() - timedelta(hours=24)
            
            result = session.execute(text("""
                SELECT 
                    COUNT(DISTINCT cu.username) as users,
                    COUNT(cu.id) as commands,
                    AVG(COALESCE(cu.execution_time_ms, 0)) as avg_time,
                    (SELECT COUNT(*) FROM analytics_error_logs WHERE timestamp >= :cutoff) as errors
                FROM analytics_command_usage cu 
                WHERE cu.timestamp >= :cutoff
            """), {"cutoff": cutoff}).fetchone()
            
            if result:
                return {
                    'total_users': int(result.users or 0),
                    'total_commands': int(result.commands or 0),
                    'avg_response_time': round(float(result.avg_time or 0), 2),
                    'error_count': int(result.errors or 0),
                    'status': 'success',
                    'timestamp': datetime.now().isoformat()
                }
            raise Exception("Sem resultados")
            
        finally:
            session.close()
    
    try:
        return jsonify(execute_with_retry(get_real_data))
    except Exception as e:
        logger.error(f"Falha ao obter dados reais: {e}")
        return jsonify(get_fallback_data())

@app.route('/api/users/active')
def active_users():
    """API para usuários ativos"""
    return jsonify({
        'active_users_24h': 8,
        'new_users_today': 2,
        'status': 'mock'
    })

@app.route('/api/commands')
def commands_stats():
    """API para comandos mais utilizados"""
    if analytics_available and is_render:
        try:
            from analytics.bot_analytics_postgresql import get_session
            from sqlalchemy import func, text
            
            session = get_session()
            if session:
                result = session.execute(text("""
                    SELECT command, COUNT(*) as count
                    FROM analytics_command_usage 
                    WHERE timestamp >= :cutoff
                    GROUP BY command 
                    ORDER BY count DESC 
                    LIMIT 10
                """), {"cutoff": datetime.now() - timedelta(days=7)}).fetchall()
                
                session.close()
                
                return jsonify({
                    'top_commands': [{'command': row.command, 'count': row.count} for row in result],
                    'status': 'success'
                })
        except Exception as e:
            logger.error(f"Erro ao obter comandos: {e}")
    
    # Mock data
    return jsonify({
        'top_commands': [
            {'command': '/start', 'count': 25},
            {'command': '/help', 'count': 18},
            {'command': '/extrato', 'count': 12},
            {'command': '/dashboard', 'count': 8}
        ],
        'status': 'mock'
    })

@app.route('/api/errors/recent')
def recent_errors():
    """API para erros recentes"""
    try:
        days = int(request.args.get('days', 3))
        
        if analytics_available and is_render:
            from analytics.bot_analytics_postgresql import get_session
            from sqlalchemy import text
            
            session = get_session()
            if session:
                errors = session.execute(text("""
                    SELECT error_type, error_message, timestamp, username, command
                    FROM analytics_error_logs 
                    WHERE timestamp >= :cutoff
                    ORDER BY timestamp DESC 
                    LIMIT 20
                """), {"cutoff": datetime.now() - timedelta(days=days)}).fetchall()
                
                session.close()
                
                return jsonify({
                    'errors': [{
                        'type': row.error_type,
                        'message': row.error_message[:100],
                        'timestamp': row.timestamp.isoformat(),
                        'user': row.username or 'N/A',
                        'command': row.command or 'N/A'
                    } for row in errors],
                    'status': 'success'
                })
        
        # Fallback
        return jsonify({
            'errors': [{
                'type': 'MockError',
                'message': 'Erro de exemplo para demonstração',
                'timestamp': datetime.now().isoformat(),
                'user': 'usuario_teste',
                'command': '/test'
            }],
            'status': 'mock'
        })
        
    except Exception as e:
        return jsonify({'error': str(e), 'status': 'error'})

if __name__ == '__main__':
    # Configurar servidor
    port = int(os.environ.get('PORT', 5000))
    debug_mode = not is_render
    
    logger.info(f"🌐 Dashboard iniciando em 0.0.0.0:{port}")
    logger.info(f"📁 Template dir: {template_dir}")
    logger.info(f"📁 Static dir: {static_dir}")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug_mode,
        use_reloader=False
    )