#!/usr/bin/env python3
"""
Dashboard Web para Analytics do MaestroFin Bot
Interface web para visualizar métricas, estatísticas e logs
"""

import os
import sys
from flask import Flask, render_template, jsonify, request
from datetime import datetime, timedelta
import json

# Configurar paths absolutos
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
template_dir = os.path.join(parent_dir, 'templates')
static_dir = os.path.join(parent_dir, 'static')

# Adicionar o diretório raiz ao Python path
sys.path.insert(0, parent_dir)

# Criar app Flask com paths corretos
app = Flask(__name__, 
           template_folder=template_dir,
           static_folder=static_dir)

# Importar analytics após configurar paths
try:
    # 🚀 RENDER: PostgreSQL, LOCAL: SQLite  
    if os.getenv('DATABASE_URL'):
        from analytics.bot_analytics_postgresql import get_analytics
        analytics = get_analytics()
        analytics_available = True
        print("✅ Analytics PostgreSQL carregado para dashboard (RENDER)")
    else:
        from analytics.bot_analytics import analytics
        analytics_available = True
        print("✅ Analytics SQLite carregado para dashboard (LOCAL)")
except ImportError as e:
    print(f"⚠️ Analytics não disponível: {e}")
    analytics_available = False

@app.route('/')
def dashboard():
    """Página principal do dashboard"""
    try:
        return render_template('dashboard_analytics_clean.html')
    except Exception as e:
        return f"""
        <h1>ERRO NO DASHBOARD</h1>
        <p><strong>Erro:</strong> {str(e)}</p>
        <p><strong>Template dir:</strong> {template_dir}</p>
        <p><strong>Template existe:</strong> {os.path.exists(os.path.join(template_dir, 'dashboard_analytics_clean.html'))}</p>
        <p><strong>Arquivos na pasta templates:</strong> {os.listdir(template_dir) if os.path.exists(template_dir) else 'Pasta não existe'}</p>
        """

@app.route('/health')
def health():
    """Health check do dashboard"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'analytics_available': analytics_available
    })

# 🚨 CORREÇÃO URGENTE - APIs completas para Analytics

@app.route('/api/realtime')
def realtime_stats():
    """API para métricas em tempo real - CORRIGIDA RENDER"""
    if not analytics_available:
        return jsonify({'error': 'Analytics não disponível'})
    
    now = datetime.now()
    
    try:
        # 🚀 RENDER: PostgreSQL vs LOCAL: SQLite
        if os.getenv('DATABASE_URL'):
            # PostgreSQL (Render)
            from analytics.bot_analytics_postgresql import get_session
            session = get_session()
            
            try:
                # Consultar dados do PostgreSQL
                from analytics.bot_analytics_postgresql import CommandUsage, ErrorLogs
                
                # Total de usuários únicos (últimas 24h)
                from sqlalchemy import func
                total_users = session.query(func.count(func.distinct(CommandUsage.username))).filter(
                    CommandUsage.timestamp >= now - timedelta(hours=24)
                ).scalar() or 0
                
                # Total de comandos (últimas 24h)
                total_commands = session.query(func.count(CommandUsage.id)).filter(
                    CommandUsage.timestamp >= now - timedelta(hours=24)
                ).scalar() or 0
                
                # Tempo médio de resposta (últimas 24h)
                avg_response = session.query(func.avg(CommandUsage.execution_time_ms)).filter(
                    CommandUsage.timestamp >= now - timedelta(hours=24),
                    CommandUsage.execution_time_ms.isnot(None)
                ).scalar() or 0
                
                # Contagem de erros (últimas 24h)
                error_count = session.query(func.count(ErrorLogs.id)).filter(
                    ErrorLogs.timestamp >= now - timedelta(hours=24)
                ).scalar() or 0
                
                session.close()
                
            except Exception as e:
                print(f"❌ Erro PostgreSQL realtime: {e}")
                if session:
                    session.close()
                # Dados default se falhar
                total_users = total_commands = error_count = 0
                avg_response = 0.0
                
        else:
            # SQLite (Local)
            import sqlite3
            conn = sqlite3.connect(analytics.db_path)
            
            # Total de usuários únicos (últimas 24h)
            total_users = conn.execute("""
                SELECT COUNT(DISTINCT username) 
                FROM command_usage 
                WHERE timestamp >= datetime('now', '-24 hours')
            """).fetchone()[0]
            
            # Total de comandos (últimas 24h)
            total_commands = conn.execute("""
                SELECT COUNT(*) 
                FROM command_usage 
                WHERE timestamp >= datetime('now', '-24 hours')
            """).fetchone()[0]
            
            # Tempo médio de resposta (últimas 24h)
            avg_response = conn.execute("""
                SELECT AVG(execution_time_ms) 
                FROM command_usage 
                WHERE timestamp >= datetime('now', '-24 hours')
                AND execution_time_ms IS NOT NULL
            """).fetchone()[0]
            
            # Contagem de erros (últimas 24h)
            error_count = conn.execute("""
                SELECT COUNT(*) 
                FROM error_logs 
                WHERE timestamp >= datetime('now', '-24 hours')
            """).fetchone()[0]
            
            conn.close()
        
        realtime_stats = {
            'total_users': total_users or 0,
            'total_commands': total_commands or 0,
            'avg_response_time': round(avg_response if avg_response else 0, 2),
            'error_count': error_count or 0
        }
        
        # Usuário mais ativo recente
        most_active_recent = conn.execute("""
            SELECT username, COUNT(*) as count
            FROM command_usage 
            WHERE timestamp >= datetime('now', '-4 hours')
            GROUP BY username
            ORDER BY count DESC
            LIMIT 1
        """).fetchone()
        
        # Comando mais usado
        most_used_command = conn.execute("""
            SELECT command, COUNT(*) as count
            FROM command_usage 
            WHERE timestamp >= datetime('now', '-24 hours')
            GROUP BY command
            ORDER BY count DESC
            LIMIT 1
        """).fetchone()
        
        # Último erro
        last_error = conn.execute("""
            SELECT error_type, error_message, command, username, timestamp
            FROM error_logs 
            ORDER BY timestamp DESC
            LIMIT 1
        """).fetchone()
    
        conn.close()
        
        return jsonify({
            'timestamp': now.isoformat(),
            'realtime_stats': realtime_stats,
            'highlights': {
                'most_active_user': dict(zip(['username', 'count'], most_active_recent)) if most_active_recent else None,
                'most_used_command': dict(zip(['command', 'count'], most_used_command)) if most_used_command else None,
                'last_error': dict(zip(['error_type', 'error_message', 'command', 'username', 'timestamp'], last_error)) if last_error else None
            }
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'timestamp': now.isoformat() if 'now' in locals() else datetime.now().isoformat()
        })

# 🔥 NOVAS APIs FALTANTES - Correção Crítica

@app.route('/api/users/active')
def get_active_users():
    """API para usuários ativos por período"""
    if not analytics_available:
        return jsonify({'error': 'Analytics não disponível'})
    
    period = request.args.get('period', '24h')
    
    try:
        import sqlite3
        conn = sqlite3.connect(analytics.db_path)
        
        # Calcular intervalo baseado no período
        if period == '24h':
            time_filter = "datetime('now', '-24 hours')"
        elif period == '7d':
            time_filter = "datetime('now', '-7 days')"
        elif period == '30d':
            time_filter = "datetime('now', '-30 days')"
        else:
            time_filter = "datetime('now', '-24 hours')"
        
        # Buscar usuários ativos
        users = conn.execute(f"""
            SELECT username, 
                   COUNT(*) as commands_count,
                   MAX(timestamp) as last_activity,
                   MIN(timestamp) as first_activity
            FROM command_usage 
            WHERE timestamp >= {time_filter}
            GROUP BY username
            ORDER BY commands_count DESC
            LIMIT 50
        """).fetchall()
        
        # Total de usuários únicos
        total_users = conn.execute(f"""
            SELECT COUNT(DISTINCT username) 
            FROM command_usage 
            WHERE timestamp >= {time_filter}
        """).fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'total_active_users': total_users,
            'period': period,
            'users': [
                {
                    'username': user[0],
                    'commands_count': user[1],
                    'last_activity': user[2],
                    'first_activity': user[3]
                } for user in users
            ]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/commands/ranking')
def get_commands_ranking():
    """API para ranking de comandos"""
    if not analytics_available:
        return jsonify({'error': 'Analytics não disponível'})
    
    days = int(request.args.get('days', 7))
    
    try:
        import sqlite3
        conn = sqlite3.connect(analytics.db_path)
        
        # Ranking de comandos com taxa de sucesso
        commands = conn.execute("""
            SELECT command,
                   COUNT(*) as total_uses,
                   SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_uses,
                   AVG(execution_time_ms) as avg_execution_time,
                   COUNT(DISTINCT username) as unique_users
            FROM command_usage 
            WHERE timestamp >= datetime('now', '-{} days')
            GROUP BY command
            ORDER BY total_uses DESC
            LIMIT 20
        """.format(days)).fetchall()
        
        conn.close()
        
        result = []
        for cmd in commands:
            success_rate = (cmd[2] / cmd[0]) * 100 if cmd[0] > 0 else 0
            result.append({
                'command': cmd[0],
                'total_uses': cmd[0],
                'successful_uses': cmd[2],
                'success_rate': round(success_rate, 1),
                'avg_execution_time': round(cmd[3] or 0, 2),
                'unique_users': cmd[4]
            })
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/performance/metrics')
def get_performance_metrics():
    """API para métricas de performance"""
    if not analytics_available:
        return jsonify({'error': 'Analytics não disponível'})
    
    hours = int(request.args.get('hours', 24))
    
    try:
        import sqlite3
        conn = sqlite3.connect(analytics.db_path)
        
        # Métricas de performance por comando
        metrics = conn.execute("""
            SELECT command,
                   COUNT(*) as count,
                   AVG(execution_time_ms) as avg_time,
                   MIN(execution_time_ms) as min_time,
                   MAX(execution_time_ms) as max_time
            FROM command_usage 
            WHERE timestamp >= datetime('now', '-{} hours')
            AND execution_time_ms IS NOT NULL
            GROUP BY command
            ORDER BY avg_time DESC
            LIMIT 20
        """.format(hours)).fetchall()
        
        conn.close()
        
        return jsonify([
            {
                'command': metric[0],
                'count': metric[1],
                'avg_time': round(metric[2] or 0, 2),
                'min_time': metric[3] or 0,
                'max_time': metric[4] or 0
            } for metric in metrics
        ])
        
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/errors/detailed')
def get_detailed_errors():
    """API para análise detalhada de erros"""
    if not analytics_available:
        return jsonify({'error': 'Analytics não disponível'})
    
    days = int(request.args.get('days', 7))
    
    try:
        import sqlite3
        conn = sqlite3.connect(analytics.db_path)
        
        # Análise de erros por tipo
        error_analysis = conn.execute("""
            SELECT error_type,
                   COUNT(*) as error_count,
                   COUNT(DISTINCT username) as affected_users,
                   MAX(timestamp) as last_occurrence
            FROM error_logs 
            WHERE timestamp >= datetime('now', '-{} days')
            GROUP BY error_type
            ORDER BY error_count DESC
        """.format(days)).fetchall()
        
        # Erros recentes
        recent_errors = conn.execute("""
            SELECT error_type, error_message, command, username, timestamp
            FROM error_logs 
            WHERE timestamp >= datetime('now', '-{} days')
            ORDER BY timestamp DESC
            LIMIT 10
        """.format(days)).fetchall()
        
        conn.close()
        
        return jsonify({
            'error_analysis': [
                {
                    'error_type': error[0],
                    'error_count': error[1],
                    'affected_users': error[2],
                    'last_occurrence': error[3]
                } for error in error_analysis
            ],
            'recent_errors': [
                {
                    'error_type': error[0],
                    'error_message': error[1][:100] + '...' if len(error[1]) > 100 else error[1],
                    'command': error[2],
                    'username': error[3],
                    'timestamp': error[4]
                } for error in recent_errors
            ]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    print("🚨 Iniciando MaestroFin Crisis Sensor Dashboard...")
    print(f"📁 Template folder: {template_dir}")
    print(f"📁 Static folder: {static_dir}")
    print(f"✅ Analytics disponível: {analytics_available}")
    print("🌐 Servidor rodando em: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
