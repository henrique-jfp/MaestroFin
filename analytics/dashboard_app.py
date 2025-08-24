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

@app.route('/api/realtime')
def realtime_stats():
    """API para métricas em tempo real"""
    if not analytics_available:
        return jsonify({'error': 'Analytics não disponível'})
    
    now = datetime.now()
    
    try:
        # Conectar ao banco de dados
        import sqlite3
        conn = sqlite3.connect(analytics.db_path)
        
        # Estatísticas em tempo real
        realtime_stats = {}
        
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

if __name__ == '__main__':
    print("🚨 Iniciando MaestroFin Crisis Sensor Dashboard...")
    print(f"📁 Template folder: {template_dir}")
    print(f"📁 Static folder: {static_dir}")
    print(f"✅ Analytics disponível: {analytics_available}")
    print("🌐 Servidor rodando em: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
