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
    # 🚀 RENDER: PostgreSQL sempre (removendo SQLite para simplificar)
    if os.getenv('DATABASE_URL'):
        from analytics.bot_analytics_postgresql import get_analytics
        analytics = get_analytics()
        analytics_available = True
        is_render = True
        print("✅ Analytics PostgreSQL carregado para dashboard (RENDER)")
    else:
        # Para ambiente local sem PostgreSQL, criar mock básico
        print("⚠️ Ambiente local sem PostgreSQL - usando modo mock")
        analytics_available = False
        is_render = False
except ImportError as e:
    print(f"⚠️ Analytics não disponível: {e}")
    analytics_available = False
    is_render = False

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
        <p><strong>Template exists:</strong> {os.path.exists(os.path.join(template_dir, 'dashboard_analytics_clean.html'))}</p>
        """

@app.route('/api/status')
def api_status():
    """Endpoint simples para verificar se a API está online e fornecer dados básicos."""
    # Em um futuro, podemos adicionar mais verificações aqui (ex: conexão com DB)
    return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat(), 'version': '1.0.0'})

@app.route('/api/realtime')
def realtime_stats():
    """API para métricas em tempo real - ULTRA ROBUSTO com RETRY"""
    
    # Fallback data que sempre funciona
    fallback_data = {
        'total_users': 15,
        'total_commands': 127,
        'avg_response_time': 245.8,
        'error_count': 3,
        'status': 'fallback_data'
    }
    
    if not analytics_available:
        return jsonify(fallback_data)
    
    # 🔄 RETRY AUTOMÁTICO para consultas SQL
    max_retries = 3
    retry_delay = 0.5
    
    for attempt in range(max_retries):
        try:
            if is_render:
                # 🚀 RENDER: PostgreSQL com proteção SSL ULTRA ROBUSTA
                from analytics.bot_analytics_postgresql import get_session, CommandUsage, ErrorLogs
                from sqlalchemy import func, exc
                import traceback
                import time
                
                session = None
                
                try:
                    print(f"🔄 Tentativa {attempt + 1}/{max_retries} de conexão PostgreSQL...")
                    
                    session = get_session()
                    if not session:
                        raise Exception("Sessão PostgreSQL não pôde ser criada")
                    
                    now = datetime.now()
                    cutoff = now - timedelta(hours=24)
                    
                    # 🔧 QUERY CORRIGIDA - usando text() para SQL raw
                    from sqlalchemy import text
                    query_result = session.execute(text("""
                        SELECT 
                            COUNT(DISTINCT cu.username) as total_users,
                            COUNT(cu.id) as total_commands,
                            AVG(COALESCE(cu.execution_time_ms, 0)) as avg_response,
                            (SELECT COUNT(*) FROM analytics_error_logs WHERE timestamp >= :cutoff2) as error_count
                        FROM analytics_command_usage cu 
                        WHERE cu.timestamp >= :cutoff1
                    """), {"cutoff1": cutoff, "cutoff2": cutoff}).fetchone()
                    
                    if query_result:
                        total_users, total_commands, avg_response, error_count = query_result
                        print(f"✅ Query SQL bem-sucedida - Usuários: {total_users}, Comandos: {total_commands}")
                        
                        result_data = {
                            'total_users': int(total_users or 0),
                            'total_commands': int(total_commands or 0),
                            'avg_response_time': round(float(avg_response or 0), 2),
                            'error_count': int(error_count or 0),
                            'status': 'success',
                            'timestamp': datetime.now().isoformat(),
                            'attempt': attempt + 1
                        }
                        
                        if session:
                            session.close()
                            print("✅ Sessão PostgreSQL fechada")
                        
                        return jsonify(result_data)
                    else:
                        raise Exception("Query não retornou resultados")
                        
                except (exc.OperationalError, Exception) as db_error:
                    print(f"❌ Erro PostgreSQL tentativa {attempt + 1}: {db_error}")
                    
                    if session:
                        try:
                            session.close()
                        except:
                            pass
                    
                    # Se não é a última tentativa, aguarda e tenta novamente
                    if attempt < max_retries - 1:
                        print(f"⏳ Aguardando {retry_delay}s antes da próxima tentativa...")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Backoff exponencial
                        continue
                    else:
                        # Última tentativa falhou, usar fallback
                        print("💥 Todas as tentativas falharam - usando dados fallback")
                        break
                        
            else:
                # Mock data para ambiente local
                return jsonify({
                    'total_users': 5,
                    'total_commands': 42,
                    'avg_response_time': 125.0,
                    'error_count': 1,
                    'status': 'local_mock',
                    'timestamp': datetime.now().isoformat()
                })
                
        except Exception as critical_error:
            print(f"💥 Erro crítico tentativa {attempt + 1}: {critical_error}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
            else:
                break
    
    # Se chegou até aqui, todas as tentativas falharam
    print("🛟 Retornando dados fallback após esgotamento de tentativas")
    return jsonify({
        **fallback_data,
        'status': 'all_retries_failed',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/users/active')
def active_users():
    """API para usuários ativos"""
    return jsonify({
        'active_users_24h': 8,
        'new_users_today': 2,
        'status': 'mock'
    })

@app.route('/api/debug')
def debug_info():
    """Endpoint de debug para diagnosticar problemas"""
    debug_data = {
        'timestamp': datetime.now().isoformat(),
        'analytics_available': analytics_available,
        'is_render': is_render,
        'environment': {
            'DATABASE_URL': 'SET' if os.getenv('DATABASE_URL') else 'NOT_SET',
            'PORT': os.getenv('PORT', 'NOT_SET'),
            'RENDER_SERVICE_NAME': os.getenv('RENDER_SERVICE_NAME', 'NOT_SET')
        },
        'ssl_tests': []
    }
    
    # Teste rápido de conectividade PostgreSQL
    if analytics_available and is_render:
        try:
            from analytics.bot_analytics_postgresql import get_session
            
            # Teste 1: Criar sessão
            debug_data['ssl_tests'].append({
                'test': 'create_session',
                'status': 'attempting'
            })
            
            session = get_session()
            if session:
                debug_data['ssl_tests'][-1]['status'] = 'success'
                
                # Teste 2: Query simples
                debug_data['ssl_tests'].append({
                    'test': 'simple_query',
                    'status': 'attempting'
                })
                
                from sqlalchemy import text
                result = session.execute(text("SELECT 1 as test")).fetchone()
                debug_data['ssl_tests'][-1]['status'] = 'success'
                debug_data['ssl_tests'][-1]['result'] = str(result)
                
                # Teste 3: Query das tabelas de analytics
                debug_data['ssl_tests'].append({
                    'test': 'analytics_tables',
                    'status': 'attempting'
                })
                
                tables = session.execute(text("""
                    SELECT table_name FROM information_schema.tables 
                    WHERE table_name LIKE 'analytics_%'
                """)).fetchall()
                
                debug_data['ssl_tests'][-1]['status'] = 'success'
                debug_data['ssl_tests'][-1]['tables'] = [t[0] for t in tables]
                
                session.close()
            else:
                debug_data['ssl_tests'][-1]['status'] = 'failed'
                debug_data['ssl_tests'][-1]['error'] = 'session_is_none'
                
        except Exception as debug_error:
            debug_data['ssl_tests'].append({
                'test': 'error_caught',
                'status': 'failed',
                'error': str(debug_error)[:200]
            })
    
    return jsonify(debug_data)

@app.route('/api/errors/detailed')
def detailed_errors():
    """API para erros detalhados"""
    try:
        days = int(request.args.get('days', 7))
        
        if analytics_available and is_render:
            from analytics.bot_analytics_postgresql import get_session, ErrorLogs
            from sqlalchemy import func
            
            session = get_session()
            if session:
                errors = session.query(ErrorLogs).filter(
                    ErrorLogs.timestamp >= datetime.now() - timedelta(days=days)
                ).order_by(ErrorLogs.timestamp.desc()).limit(50).all()
                
                error_list = [{
                    'timestamp': error.timestamp.isoformat(),
                    'error_type': error.error_type,
                    'message': error.error_message[:100],
                    'command': error.command,
                    'username': error.username
                } for error in errors]
                
                session.close()
                
                return jsonify({
                    'errors': error_list,
                    'count': len(error_list),
                    'status': 'success'
                })
        
        # Fallback/mock
        return jsonify({
            'errors': [
                {
                    'timestamp': datetime.now().isoformat(),
                    'error_type': 'MockError', 
                    'message': 'Erro de exemplo para teste',
                    'command': '/test',
                    'username': 'usuario_teste'
                }
            ],
            'count': 1,
            'status': 'mock'
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'error'
        })

@app.route('/api/commands')
def commands_stats():
    """API simplificada para comandos"""
    try:
        if analytics_available and is_render:
            from analytics.bot_analytics_postgresql import get_session, CommandUsage
            from sqlalchemy import func
            session = get_session()
            
            if session:
                top_commands = session.query(
                    CommandUsage.command, 
                    func.count(CommandUsage.id).label('count')
                ).filter(
                    CommandUsage.timestamp >= datetime.now() - timedelta(days=7)
                ).group_by(CommandUsage.command).order_by(
                    func.count(CommandUsage.id).desc()
                ).limit(10).all()
                
                session.close()
                
                return jsonify({
                    'top_commands': [{'command': cmd, 'count': int(cnt)} for cmd, cnt in top_commands],
                    'status': 'ok'
                })
        
        # Mock data
        return jsonify({
            'top_commands': [
                {'command': '/start', 'count': 25},
                {'command': '/help', 'count': 18},
                {'command': '/extrato', 'count': 12},
                {'command': '/ocr', 'count': 8},
                {'command': '/contact', 'count': 5}
            ],
            'status': 'mock'
        })
            
    except Exception as e:
        print(f"❌ Erro commands API: {e}")
        return jsonify({'error': str(e), 'status': 'error'})

@app.route('/api/users')
def users_stats():
    """API simplificada para usuários"""
    try:
        return jsonify({
            'active_users': 10,
            'new_users_today': 2,
            'status': 'simplified'
        })
    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    # Verificar se templates e static existem
    print(f"🌐 Dashboard iniciando em 0.0.0.0:5000")
    print(f"📁 Template dir: {template_dir}")
    print(f"📁 Static dir: {static_dir}")
    
    template_file = os.path.join(template_dir, 'dashboard_analytics_clean.html')
    css_file = os.path.join(static_dir, 'dashboard_cyberpunk.css')
    
    print(f"✅ Template: {'OK' if os.path.exists(template_file) else 'MISSING'}")
    print(f"✅ CSS: {'OK' if os.path.exists(css_file) else 'MISSING'}")
    
    print("🚀 Iniciando servidor Flask...")
    app.run(host='0.0.0.0', port=5000, debug=True)