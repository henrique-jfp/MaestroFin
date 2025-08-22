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
    date = request.args.get('date')
    stats = analytics.get_daily_stats(date)
    return jsonify(stats)

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

if __name__ == '__main__':
    # Verificar se analytics está disponível e inicializar
    if analytics_available:
        analytics.init_database()
        print("✅ Database inicializada!")
    else:
        print("⚠️ Analytics não disponível - modo de teste")
    
    print("🚀 Analytics Dashboard iniciado!")
    print("📊 Acesse: http://localhost:5000")
    print("❤️ Health check: http://localhost:5000/health")
    print("🔄 Auto-refresh: 30 segundos")
    print("💡 Pressione Ctrl+C para parar")
    
    app.run(host='0.0.0.0', port=5000, debug=False)
