#!/usr/bin/env python3
"""
Script para popular o banco de analytics com dados de teste
Para mostrar o dashboard funcionando mesmo sem uso real
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlite3
import random
from datetime import datetime, timedelta
from analytics.bot_analytics import analytics

def populate_test_data():
    """Popula o banco com dados de teste realistas"""
    
    print("🚀 Populando banco de analytics com dados de teste...")
    
    # Lista de comandos simulados
    commands = [
        '/start', '/ajuda', '/novo_lancamento', '/extrato', '/metas', 
        '/categorias', '/relatorio', '/dashboard', '/configuracoes',
        '/backup', '/gamification', '/estatisticas'
    ]
    
    # Lista de usuários simulados
    users = [
        {'id': 123456789, 'username': 'henrique_jfp'},
        {'id': 987654321, 'username': 'user_teste'},
        {'id': 456789123, 'username': 'maria_silva'},
        {'id': 789123456, 'username': 'joao_santos'},
        {'id': 321654987, 'username': 'ana_costa'},
    ]
    
    # Tipos de erro simulados
    error_types = [
        'DatabaseError', 'OCRError', 'ValidationError', 
        'APIError', 'TimeoutError', 'AuthenticationError'
    ]
    
    # Gerar dados dos últimos 30 dias
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    conn = sqlite3.connect(analytics.db_path)
    
    # Limpar dados existentes (opcional)
    # conn.execute("DELETE FROM command_usage")
    # conn.execute("DELETE FROM error_logs") 
    # conn.execute("DELETE FROM daily_users")
    
    print("📊 Gerando dados de comandos...")
    
    # Gerar dados de comando por dia
    for day in range(30):
        current_date = start_date + timedelta(days=day)
        
        # Mais atividade nos fins de semana e menos durante a madrugada
        if current_date.weekday() in [5, 6]:  # Sábado e Domingo
            daily_commands = random.randint(50, 150)
        else:
            daily_commands = random.randint(20, 80)
        
        for _ in range(daily_commands):
            # Selecionar usuário e comando aleatório
            user = random.choice(users)
            command = random.choice(commands)
            
            # Simular horário mais realista (menos atividade de madrugada)
            hour = random.choices(
                range(24),
                weights=[1,1,1,2,2,3,5,8,10,12,15,18,20,18,15,12,10,8,5,3,2,2,1,1]
            )[0]
            
            timestamp = current_date.replace(
                hour=hour,
                minute=random.randint(0, 59),
                second=random.randint(0, 59)
            )
            
            # 95% de sucesso, 5% de erro
            success = random.random() > 0.05
            execution_time = random.randint(50, 2000)  # 50ms a 2s
            
            # Inserir comando
            conn.execute("""
                INSERT INTO command_usage (user_id, username, command, timestamp, success, execution_time_ms)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user['id'], user['username'], command, timestamp, success, execution_time))
            
            # Inserir erro ocasionalmente
            if not success:
                error_type = random.choice(error_types)
                error_message = f"Erro simulado em {command}: {error_type}"
                
                conn.execute("""
                    INSERT INTO error_logs (user_id, username, command, error_type, error_message, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (user['id'], user['username'], command, error_type, error_message, timestamp))
    
    print("👥 Gerando dados de usuários diários...")
    
    # Gerar dados de usuários diários
    for day in range(30):
        current_date = start_date + timedelta(days=day)
        
        # Usuários ativos por dia (entre 60% e 100% dos usuários)
        active_users = random.sample(users, random.randint(3, len(users)))
        
        for user in active_users:
            commands_count = random.randint(1, 25)
            first_command = random.choice(commands)
            
            conn.execute("""
                INSERT OR REPLACE INTO daily_users (user_id, username, date, first_command, total_commands)
                VALUES (?, ?, ?, ?, ?)
            """, (user['id'], user['username'], current_date.date(), first_command, commands_count))
    
    print("🎯 Gerando métricas de performance...")
    
    # Gerar algumas métricas de performance
    metrics = [
        ('active_users_24h', random.randint(15, 35)),
        ('commands_per_hour', random.randint(5, 15)),
        ('avg_response_time', random.randint(200, 800)),
        ('error_rate_percent', random.uniform(1, 5))
    ]
    
    for metric_name, value in metrics:
        for hour in range(24):
            timestamp = datetime.now().replace(hour=hour, minute=0, second=0) - timedelta(hours=hour)
            fluctuation = value * random.uniform(0.8, 1.2)  # Variação de ±20%
            
            conn.execute("""
                INSERT INTO performance_metrics (metric_name, metric_value, timestamp)
                VALUES (?, ?, ?)
            """, (metric_name, fluctuation, timestamp))
    
    conn.commit()
    conn.close()
    
    print("✅ Dados de teste inseridos com sucesso!")
    print(f"📊 Período: {start_date.date()} até {end_date.date()}")
    print(f"👥 {len(users)} usuários simulados")
    print(f"⚡ {len(commands)} tipos de comando")
    print(f"🚨 {len(error_types)} tipos de erro")
    
    # Mostrar algumas estatísticas
    conn = sqlite3.connect(analytics.db_path)
    
    total_commands = conn.execute("SELECT COUNT(*) FROM command_usage").fetchone()[0]
    total_errors = conn.execute("SELECT COUNT(*) FROM error_logs").fetchone()[0]
    total_users = conn.execute("SELECT COUNT(DISTINCT user_id) FROM daily_users").fetchone()[0]
    
    print(f"\n📈 Estatísticas geradas:")
    print(f"   • Total de comandos: {total_commands}")
    print(f"   • Total de erros: {total_errors}")
    print(f"   • Usuários únicos: {total_users}")
    print(f"   • Taxa de erro: {(total_errors/total_commands*100):.1f}%")
    
    conn.close()

if __name__ == "__main__":
    populate_test_data()
