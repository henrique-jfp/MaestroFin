#!/usr/bin/env python3
"""
Dashboa@app.route('/')
def dashboard():
    """Página principal do dashboard"""
    try:
        return render_template('dashboard_analytics_clean.html')
    except Exception as e:
        return f"""
        <h1>🚨 ERRO NO DASHBOARD</h1>
        <p><strong>Erro:</strong> {str(e)}</p>
        <p><strong>Template dir:</strong> {template_dir}</p>
        <p><strong>Template existe:</strong> {os.path.exists(os.path.join(template_dir, 'dashboard_analytics_clean.html'))}</p>
        <p><strong>Arquivos na pasta templates:</strong> {os.listdir(template_dir) if os.path.exists(template_dir) else 'Pasta não existe'}</p>
        """nalytics do MaestroFin Bot
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
    from analytics.bot_analytics import analytics
    analytics_available = True
except ImportError as e:
    print(f"⚠️ Analytics não disponível: {e}")
    analytics_available = False

@app.route('/')
def dashboard():
    """Página principal do dashboard"""
    try:
        return render_template('dashboard_analytics.html')
    except Exception as e:
        return f"""
        <h1>🚨 ERRO NO DASHBOARD</h1>
        <p><strong>Erro:</strong> {str(e)}</p>
        <p><strong>Template dir:</strong> {template_dir}</p>
        <p><strong>Template existe:</strong> {os.path.exists(os.path.join(template_dir, 'dashboard_analytics.html'))}</p>
        <p><strong>Arquivos na pasta templates:</strong> {os.listdir(template_dir) if os.path.exists(template_dir) else 'Pasta não existe'}</p>
        """

@app.route('/health')
def health():
    """Health check do dashboard"""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "analytics_available": analytics_available,
        "template_dir": template_dir,
        "template_exists": os.path.exists(os.path.join(template_dir, 'dashboard_analytics.html'))
    })

@app.route('/api/stats/daily')
def api_daily_stats():
    """API: Estatísticas diárias"""
    date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    
    import sqlite3
    with sqlite3.connect(analytics.db_path) as conn:
        conn.row_factory = sqlite3.Row
        
        # Stats básicas do dia
        daily_stats = conn.execute("""
            SELECT 
                COUNT(DISTINCT user_id) as unique_users,
                COUNT(*) as total_commands,
                AVG(execution_time_ms) as avg_response_time,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_commands,
                SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed_commands
            FROM command_usage 
            WHERE DATE(timestamp) = ?
        """, (date,)).fetchone()
        
        # Usuários mais ativos do dia
        top_users = conn.execute("""
            SELECT username, user_id, COUNT(*) as commands_count
            FROM command_usage 
            WHERE DATE(timestamp) = ? AND username IS NOT NULL
            GROUP BY user_id, username
            ORDER BY commands_count DESC
            LIMIT 10
        """, (date,)).fetchall()
        
        # Horários de maior atividade
        hourly_activity = conn.execute("""
            SELECT 
                strftime('%H:00', timestamp) as hour,
                COUNT(*) as commands,
                COUNT(DISTINCT user_id) as unique_users
            FROM command_usage 
            WHERE DATE(timestamp) = ?
            GROUP BY strftime('%H', timestamp)
            ORDER BY hour
        """, (date,)).fetchall()
        
        # Comandos mais usados
        top_commands = conn.execute("""
            SELECT 
                command, 
                COUNT(*) as count,
                COUNT(DISTINCT user_id) as unique_users,
                AVG(execution_time_ms) as avg_time,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successes,
                SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as errors
            FROM command_usage 
            WHERE DATE(timestamp) = ?
            GROUP BY command 
            ORDER BY count DESC
        """, (date,)).fetchall()
        
        # Novos usuários do dia
        new_users = conn.execute("""
            SELECT username, user_id, first_command, total_commands
            FROM daily_users 
            WHERE date = ?
            ORDER BY total_commands DESC
        """, (date,)).fetchall()
    
    return jsonify({
        'date': date,
        'overview': dict(daily_stats) if daily_stats else {},
        'top_users': [dict(row) for row in top_users],
        'hourly_activity': [dict(row) for row in hourly_activity],
        'top_commands': [dict(row) for row in top_commands],
        'new_users': [dict(row) for row in new_users]
    })

@app.route('/api/stats/weekly')
def api_weekly_stats():
    """API: Estatísticas semanais"""
    weeks_back = int(request.args.get('weeks_back', 0))
    stats = analytics.get_weekly_stats(weeks_back)
    return jsonify(stats)

@app.route('/api/stats/monthly')
def api_monthly_stats():
    """API: Estatísticas mensais"""
    # Últimos 30 dias
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=29)
    
    with analytics.db_path as db:
        # Implementar lógica mensal aqui
        pass
    
    return jsonify({'status': 'em desenvolvimento'})

@app.route('/api/commands/ranking')
def api_commands_ranking():
    """API: Ranking de comandos mais usados"""
    days = int(request.args.get('days', 7))
    cutoff_date = datetime.now() - timedelta(days=days)
    
    import sqlite3
    with sqlite3.connect(analytics.db_path) as conn:
        conn.row_factory = sqlite3.Row
        
        ranking = conn.execute("""
            SELECT command, 
                   COUNT(*) as total_uses,
                   COUNT(DISTINCT user_id) as unique_users,
                   AVG(execution_time_ms) as avg_time,
                   SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successes,
                   SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as errors
            FROM command_usage 
            WHERE timestamp >= ?
            GROUP BY command
            ORDER BY total_uses DESC
        """, (cutoff_date,)).fetchall()
        
        return jsonify([dict(row) for row in ranking])

@app.route('/api/donations/stats')
def api_donation_stats():
    """API: Estatísticas de doações"""
    return jsonify(analytics.get_donation_stats())

@app.route('/api/errors/summary')
def api_errors_summary():
    """API: Resumo de erros"""
    days = int(request.args.get('days', 7))
    return jsonify(analytics.get_error_summary(days))

@app.route('/api/users/growth')
def api_user_growth():
    """API: Crescimento de usuários"""
    days = int(request.args.get('days', 30))
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days-1)
    
    import sqlite3
    with sqlite3.connect(analytics.db_path) as conn:
        conn.row_factory = sqlite3.Row
        
        growth_data = conn.execute("""
            SELECT date, COUNT(*) as new_users,
                   SUM(total_commands) as total_commands
            FROM daily_users 
            WHERE date BETWEEN ? AND ?
            GROUP BY date
            ORDER BY date
        """, (start_date, end_date)).fetchall()
        
        # Calcular usuários acumulados
        cumulative_users = 0
        result = []
        for row in growth_data:
            cumulative_users += row['new_users']
            result.append({
                'date': row['date'],
                'new_users': row['new_users'],
                'cumulative_users': cumulative_users,
                'total_commands': row['total_commands']
            })
        
        return jsonify(result)

@app.route('/api/performance/metrics')
def api_performance_metrics():
    """API: Métricas de performance"""
    hours = int(request.args.get('hours', 24))
    cutoff_time = datetime.now() - timedelta(hours=hours)
    
    import sqlite3
    with sqlite3.connect(analytics.db_path) as conn:
        conn.row_factory = sqlite3.Row
        
        # Tempo médio de resposta por comando
        response_times = conn.execute("""
            SELECT command, 
                   AVG(execution_time_ms) as avg_time,
                   MIN(execution_time_ms) as min_time,
                   MAX(execution_time_ms) as max_time,
                   COUNT(*) as count
            FROM command_usage 
            WHERE timestamp >= ? AND success = 1
            GROUP BY command
            HAVING count >= 5
            ORDER BY avg_time DESC
        """, (cutoff_time,)).fetchall()
        
        return jsonify([dict(row) for row in response_times])

@app.route('/api/live/stats')
def api_live_stats():
    """API: Estatísticas em tempo real (últimas 24h)"""
    last_24h = datetime.now() - timedelta(hours=24)
    
    import sqlite3
    with sqlite3.connect(analytics.db_path) as conn:
        conn.row_factory = sqlite3.Row
        
        # Comandos por hora nas últimas 24h
        hourly_commands = conn.execute("""
            SELECT strftime('%H:00', timestamp) as hour,
                   COUNT(*) as commands
            FROM command_usage 
            WHERE timestamp >= ?
            GROUP BY strftime('%H', timestamp)
            ORDER BY hour
        """, (last_24h,)).fetchall()
        
        # Usuários ativos agora
        active_users = conn.execute("""
            SELECT COUNT(DISTINCT user_id) as count
            FROM command_usage 
            WHERE timestamp >= ?
        """, (datetime.now() - timedelta(minutes=30),)).fetchone()['count']
        
        # Erros na última hora
        recent_errors = conn.execute("""
            SELECT COUNT(*) as count
            FROM error_logs 
            WHERE timestamp >= ?
        """, (datetime.now() - timedelta(hours=1),)).fetchone()['count']
        
        return jsonify({
            'hourly_commands': [dict(row) for row in hourly_commands],
            'active_users_30min': active_users,
            'errors_last_hour': recent_errors,
            'timestamp': datetime.now().isoformat()
        })

# ===== APIS PARA BOT TELEGRAM =====

@app.route('/api/status')
def api_status():
    """API de status para verificação do bot"""
    return jsonify({
        'status': 'online',
        'uptime': 'N/A',
        'version': '1.0.0',
        'active_sessions': 1,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/gerar-token/<int:user_id>')
def gerar_token(user_id):
    """Gera token temporário para acesso ao dashboard"""
    import secrets
    import base64
    
    # Gerar token único
    token = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8')[:16]
    
    # URL para o dashboard com filtro do usuário
    url = f"/dashboard/user/{token}?user_id={user_id}"
    
    return jsonify({
        'token': token,
        'url': url,
        'user_id': user_id,
        'expires': 24,  # horas
        'timestamp': datetime.now().isoformat()
    })

@app.route('/dashboard/user/<token>')
def dashboard_user(token):
    """Dashboard personalizado para usuário com token"""
    user_id = request.args.get('user_id', type=int)
    
    # Por enquanto, redireciona para o dashboard principal
    # Em uma implementação completa, validaria o token e filtraria dados
    return render_template('dashboard_analytics.html', user_id=user_id)

@app.route('/api/users/active')
def api_active_users():
    """API: Usuários ativos por período"""
    period = request.args.get('period', '24h')  # 1h, 24h, 7d, 30d
    
    # Calcular data de corte baseada no período
    if period == '1h':
        cutoff = datetime.now() - timedelta(hours=1)
    elif period == '24h':
        cutoff = datetime.now() - timedelta(hours=24)
    elif period == '7d':
        cutoff = datetime.now() - timedelta(days=7)
    elif period == '30d':
        cutoff = datetime.now() - timedelta(days=30)
    else:
        cutoff = datetime.now() - timedelta(hours=24)
    
    import sqlite3
    with sqlite3.connect(analytics.db_path) as conn:
        conn.row_factory = sqlite3.Row
        
        # Usuários ativos no período
        active_users = conn.execute("""
            SELECT 
                user_id,
                username,
                COUNT(*) as commands_count,
                MAX(timestamp) as last_activity,
                MIN(timestamp) as first_activity,
                AVG(execution_time_ms) as avg_response_time,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_commands,
                SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed_commands
            FROM command_usage 
            WHERE timestamp >= ? AND username IS NOT NULL
            GROUP BY user_id, username
            ORDER BY commands_count DESC
        """, (cutoff,)).fetchall()
        
        # Top comandos por usuário (apenas top 5 usuários)
        top_users_commands = {}
        for user in active_users[:5]:
            user_commands = conn.execute("""
                SELECT command, COUNT(*) as count
                FROM command_usage 
                WHERE user_id = ? AND timestamp >= ?
                GROUP BY command
                ORDER BY count DESC
                LIMIT 5
            """, (user['user_id'], cutoff)).fetchall()
            top_users_commands[user['user_id']] = [dict(cmd) for cmd in user_commands]
    
    return jsonify({
        'period': period,
        'cutoff_time': cutoff.isoformat(),
        'total_active_users': len(active_users),
        'users': [dict(row) for row in active_users],
        'top_users_commands': top_users_commands
    })

@app.route('/api/users/retention')
def api_user_retention():
    """API: Análise de retenção de usuários"""
    days_back = int(request.args.get('days', 30))
    
    import sqlite3
    with sqlite3.connect(analytics.db_path) as conn:
        conn.row_factory = sqlite3.Row
        
        # Usuários por dia de cadastro
        user_cohorts = conn.execute("""
            WITH first_usage AS (
                SELECT 
                    user_id,
                    username,
                    DATE(MIN(timestamp)) as first_date,
                    COUNT(DISTINCT DATE(timestamp)) as active_days
                FROM command_usage
                WHERE DATE(timestamp) >= date('now', '-{} days')
                GROUP BY user_id
            )
            SELECT 
                first_date,
                COUNT(*) as new_users,
                AVG(active_days) as avg_active_days,
                COUNT(CASE WHEN active_days > 1 THEN 1 END) as returned_users
            FROM first_usage
            GROUP BY first_date
            ORDER BY first_date DESC
        """.format(days_back)).fetchall()
        
        # Usuários que voltaram após X dias
        retention_analysis = conn.execute("""
            WITH user_activity AS (
                SELECT 
                    user_id,
                    DATE(MIN(timestamp)) as first_date,
                    MAX(DATE(timestamp)) as last_date,
                    COUNT(DISTINCT DATE(timestamp)) as active_days,
                    julianday(MAX(timestamp)) - julianday(MIN(timestamp)) as lifecycle_days
                FROM command_usage
                WHERE DATE(timestamp) >= date('now', '-{} days')
                GROUP BY user_id
            )
            SELECT 
                CASE 
                    WHEN active_days = 1 THEN 'One-time users'
                    WHEN lifecycle_days <= 1 THEN 'Same day return'
                    WHEN lifecycle_days <= 7 THEN 'Weekly return'
                    WHEN lifecycle_days <= 30 THEN 'Monthly return'
                    ELSE 'Long-term users'
                END as retention_category,
                COUNT(*) as user_count,
                AVG(active_days) as avg_active_days
            FROM user_activity
            GROUP BY retention_category
        """.format(days_back)).fetchall()
    
    return jsonify({
        'days_analyzed': days_back,
        'cohorts': [dict(row) for row in user_cohorts],
        'retention_analysis': [dict(row) for row in retention_analysis]
    })

@app.route('/api/commands/detailed')
def api_commands_detailed():
    """API: Análise detalhada de comandos"""
    days = int(request.args.get('days', 7))
    cutoff_date = datetime.now() - timedelta(days=days)
    
    import sqlite3
    with sqlite3.connect(analytics.db_path) as conn:
        conn.row_factory = sqlite3.Row
        
        # Análise completa de comandos
        command_analysis = conn.execute("""
            SELECT 
                command,
                COUNT(*) as total_uses,
                COUNT(DISTINCT user_id) as unique_users,
                AVG(execution_time_ms) as avg_execution_time,
                MIN(execution_time_ms) as min_execution_time,
                MAX(execution_time_ms) as max_execution_time,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_uses,
                SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed_uses,
                ROUND(AVG(CASE WHEN success = 1 THEN 100.0 ELSE 0.0 END), 2) as success_rate,
                COUNT(*) * 100.0 / SUM(COUNT(*)) OVER() as usage_percentage
            FROM command_usage 
            WHERE timestamp >= ?
            GROUP BY command
            ORDER BY total_uses DESC
        """, (cutoff_date,)).fetchall()
        
        # Comandos por dia (para gráfico de tendência)
        daily_command_trends = conn.execute("""
            SELECT 
                DATE(timestamp) as date,
                command,
                COUNT(*) as uses
            FROM command_usage 
            WHERE timestamp >= ?
            GROUP BY DATE(timestamp), command
            ORDER BY date DESC, uses DESC
        """, (cutoff_date,)).fetchall()
        
        # Horário preferencial por comando
        command_hourly_patterns = conn.execute("""
            SELECT 
                command,
                strftime('%H', timestamp) as hour,
                COUNT(*) as uses
            FROM command_usage 
            WHERE timestamp >= ?
            GROUP BY command, strftime('%H', timestamp)
            HAVING COUNT(*) >= 5
            ORDER BY command, hour
        """, (cutoff_date,)).fetchall()
    
    return jsonify({
        'period_days': days,
        'command_analysis': [dict(row) for row in command_analysis],
        'daily_trends': [dict(row) for row in daily_command_trends],
        'hourly_patterns': [dict(row) for row in command_hourly_patterns]
    })

@app.route('/api/errors/detailed')
def api_errors_detailed():
    """API: Análise detalhada de erros"""
    days = int(request.args.get('days', 7))
    cutoff_date = datetime.now() - timedelta(days=days)
    
    import sqlite3
    with sqlite3.connect(analytics.db_path) as conn:
        conn.row_factory = sqlite3.Row
        
        # Erros por tipo e frequência
        error_analysis = conn.execute("""
            SELECT 
                error_type,
                COUNT(*) as error_count,
                COUNT(DISTINCT user_id) as affected_users,
                COUNT(DISTINCT command) as affected_commands,
                MAX(timestamp) as last_occurrence,
                MIN(timestamp) as first_occurrence
            FROM error_logs 
            WHERE timestamp >= ?
            GROUP BY error_type
            ORDER BY error_count DESC
        """, (cutoff_date,)).fetchall()
        
        # Erros por comando
        errors_by_command = conn.execute("""
            SELECT 
                command,
                error_type,
                COUNT(*) as error_count,
                COUNT(DISTINCT user_id) as affected_users
            FROM error_logs 
            WHERE timestamp >= ? AND command IS NOT NULL
            GROUP BY command, error_type
            ORDER BY error_count DESC
        """, (cutoff_date,)).fetchall()
        
        # Usuários mais afetados por erros
        users_with_errors = conn.execute("""
            SELECT 
                user_id,
                username,
                COUNT(*) as error_count,
                COUNT(DISTINCT error_type) as different_errors,
                MAX(timestamp) as last_error
            FROM error_logs 
            WHERE timestamp >= ? AND user_id IS NOT NULL
            GROUP BY user_id, username
            ORDER BY error_count DESC
            LIMIT 20
        """, (cutoff_date,)).fetchall()
        
        # Timeline de erros (últimas 24h)
        recent_error_timeline = conn.execute("""
            SELECT 
                strftime('%Y-%m-%d %H:00', timestamp) as hour,
                COUNT(*) as error_count,
                COUNT(DISTINCT error_type) as different_errors
            FROM error_logs 
            WHERE timestamp >= datetime('now', '-24 hours')
            GROUP BY strftime('%Y-%m-%d %H', timestamp)
            ORDER BY hour DESC
        """).fetchall()
    
    return jsonify({
        'period_days': days,
        'error_analysis': [dict(row) for row in error_analysis],
        'errors_by_command': [dict(row) for row in errors_by_command],
        'users_with_errors': [dict(row) for row in users_with_errors],
        'recent_timeline': [dict(row) for row in recent_error_timeline]
    })

@app.route('/api/performance/detailed')
def api_performance_detailed():
    """API: Métricas detalhadas de performance"""
    hours = int(request.args.get('hours', 24))
    cutoff_time = datetime.now() - timedelta(hours=hours)
    
    import sqlite3
    with sqlite3.connect(analytics.db_path) as conn:
        conn.row_factory = sqlite3.Row
        
        # Performance por comando
        command_performance = conn.execute("""
            SELECT 
                command,
                COUNT(*) as total_executions,
                AVG(execution_time_ms) as avg_time,
                MIN(execution_time_ms) as min_time,
                MAX(execution_time_ms) as max_time,
                -- Percentis aproximados
                (SELECT execution_time_ms FROM command_usage c2 
                 WHERE c2.command = c1.command AND c2.timestamp >= ? AND c2.success = 1
                 ORDER BY execution_time_ms 
                 LIMIT 1 OFFSET (COUNT(*) * 50 / 100)) as median_time,
                (SELECT execution_time_ms FROM command_usage c2 
                 WHERE c2.command = c1.command AND c2.timestamp >= ? AND c2.success = 1
                 ORDER BY execution_time_ms 
                 LIMIT 1 OFFSET (COUNT(*) * 95 / 100)) as p95_time
            FROM command_usage c1
            WHERE timestamp >= ? AND success = 1
            GROUP BY command
            HAVING total_executions >= 5
            ORDER BY avg_time DESC
        """, (cutoff_time, cutoff_time, cutoff_time)).fetchall()
        
        # Performance ao longo do tempo
        performance_timeline = conn.execute("""
            SELECT 
                strftime('%Y-%m-%d %H:00', timestamp) as hour,
                AVG(execution_time_ms) as avg_response_time,
                COUNT(*) as total_commands,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_commands
            FROM command_usage 
            WHERE timestamp >= ?
            GROUP BY strftime('%Y-%m-%d %H', timestamp)
            ORDER BY hour
        """, (cutoff_time,)).fetchall()
        
        # Comandos mais lentos (worst performers)
        slowest_executions = conn.execute("""
            SELECT 
                command,
                user_id,
                username,
                execution_time_ms,
                timestamp,
                success
            FROM command_usage 
            WHERE timestamp >= ? AND execution_time_ms > 1000
            ORDER BY execution_time_ms DESC
            LIMIT 50
        """, (cutoff_time,)).fetchall()
    
    return jsonify({
        'period_hours': hours,
        'command_performance': [dict(row) for row in command_performance],
        'timeline': [dict(row) for row in performance_timeline],
        'slowest_executions': [dict(row) for row in slowest_executions]
    })

@app.route('/api/overview/realtime')
def api_realtime_overview():
    """API: Overview em tempo real"""
    import sqlite3
    with sqlite3.connect(analytics.db_path) as conn:
        conn.row_factory = sqlite3.Row
        
        now = datetime.now()
        
        # Últimos 30 minutos
        last_30min = now - timedelta(minutes=30)
        # Última 1 hora  
        last_1hour = now - timedelta(hours=1)
        # Últimas 24 horas
        last_24hours = now - timedelta(hours=24)
        # Última semana
        last_week = now - timedelta(days=7)
        
        # Métricas em tempo real
        realtime_stats = {
            'last_30min': dict(conn.execute("""
                SELECT 
                    COUNT(*) as commands,
                    COUNT(DISTINCT user_id) as users,
                    AVG(execution_time_ms) as avg_response_time,
                    SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as errors
                FROM command_usage WHERE timestamp >= ?
            """, (last_30min,)).fetchone()),
            
            'last_1hour': dict(conn.execute("""
                SELECT 
                    COUNT(*) as commands,
                    COUNT(DISTINCT user_id) as users,
                    AVG(execution_time_ms) as avg_response_time,
                    SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as errors
                FROM command_usage WHERE timestamp >= ?
            """, (last_1hour,)).fetchone()),
            
            'last_24hours': dict(conn.execute("""
                SELECT 
                    COUNT(*) as commands,
                    COUNT(DISTINCT user_id) as users,
                    AVG(execution_time_ms) as avg_response_time,
                    SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as errors
                FROM command_usage WHERE timestamp >= ?
            """, (last_24hours,)).fetchone()),
            
            'last_week': dict(conn.execute("""
                SELECT 
                    COUNT(*) as commands,
                    COUNT(DISTINCT user_id) as users,
                    AVG(execution_time_ms) as avg_response_time,
                    SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as errors
                FROM command_usage WHERE timestamp >= ?
            """, (last_week,)).fetchone())
        }
        
        # Usuário mais ativo recentemente
        most_active_recent = conn.execute("""
            SELECT username, user_id, COUNT(*) as commands
            FROM command_usage 
            WHERE timestamp >= ? AND username IS NOT NULL
            GROUP BY user_id, username
            ORDER BY commands DESC
            LIMIT 1
        """, (last_1hour,)).fetchone()
        
        # Comando mais usado recentemente
        most_used_command = conn.execute("""
            SELECT command, COUNT(*) as uses
            FROM command_usage 
            WHERE timestamp >= ?
            GROUP BY command
            ORDER BY uses DESC
            LIMIT 1
        """, (last_1hour,)).fetchone()
        
        # Último erro
        last_error = conn.execute("""
            SELECT error_type, error_message, command, username, timestamp
            FROM error_logs 
            ORDER BY timestamp DESC
            LIMIT 1
        """).fetchone()
    
    return jsonify({
        'timestamp': now.isoformat(),
        'realtime_stats': realtime_stats,
        'highlights': {
            'most_active_user': dict(most_active_recent) if most_active_recent else None,
            'most_used_command': dict(most_used_command) if most_used_command else None,
            'last_error': dict(last_error) if last_error else None
        }
    })

if __name__ == '__main__':
    print("🚨 Iniciando MaestroFin Crisis Sensor Dashboard...")
    print(f"📁 Template folder: {template_dir}")
    print(f"📁 Static folder: {static_dir}")
    print(f"✅ Analytics disponível: {analytics_available}")
    print("🌐 Servidor rodando em: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
