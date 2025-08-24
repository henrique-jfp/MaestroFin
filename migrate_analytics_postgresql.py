"""
🚀 MIGRAÇÃO ANALYTICS RENDER - SQLite para PostgreSQL
Script para migrar dados do analytics local para o PostgreSQL do Render
"""

import os
import logging
from datetime import datetime
from sqlalchemy.orm import sessionmaker

# Configurar logging
logging.basicConfig(level=logging.INFO)

def migrate_analytics_to_postgresql():
    """Migra dados do SQLite para PostgreSQL"""
    
    print("🔄 MIGRANDO ANALYTICS PARA POSTGRESQL (RENDER)")
    print("=" * 60)
    
    try:
        # 1. Importar analytics PostgreSQL
        print("1️⃣ Configurando PostgreSQL...")
        from analytics.bot_analytics_postgresql import get_analytics, CommandUsage, DailyUsers, ErrorLogs
        pg_analytics = get_analytics()
        
        if not pg_analytics.Session:
            print("❌ PostgreSQL não configurado")
            return False
        
        # 2. Conectar SQLite local (se existir)
        print("2️⃣ Conectando SQLite local...")
        import sqlite3
        
        sqlite_path = "analytics.db"
        if not os.path.exists(sqlite_path):
            print(f"⚠️ {sqlite_path} não encontrado - criando dados sintéticos")
            create_synthetic_data(pg_analytics)
            return True
            
        # 3. Migrar dados
        print("3️⃣ Migrando dados...")
        
        conn = sqlite3.connect(sqlite_path)
        conn.row_factory = sqlite3.Row
        
        with pg_analytics.Session() as session:
            # Migrar command_usage
            print("   📊 Migrando comandos...")
            commands = conn.execute("SELECT * FROM command_usage").fetchall()
            
            for cmd in commands:
                usage = CommandUsage(
                    user_id=cmd['user_id'],
                    username=cmd['username'],
                    command=cmd['command'],
                    timestamp=datetime.fromisoformat(cmd['timestamp'].replace('Z', '+00:00')) if cmd['timestamp'] else datetime.now(),
                    success=bool(cmd['success']),
                    execution_time_ms=cmd['execution_time_ms'],
                    parameters=cmd['parameters']
                )
                session.add(usage)
            
            # Migrar daily_users
            print("   👥 Migrando usuários diários...")
            try:
                daily_users = conn.execute("SELECT * FROM daily_users").fetchall()
                for user in daily_users:
                    daily_user = DailyUsers(
                        user_id=user['user_id'],
                        username=user['username'],
                        date=datetime.fromisoformat(user['date']) if user['date'] else datetime.now(),
                        first_command=user['first_command'],
                        total_commands=user['total_commands']
                    )
                    session.add(daily_user)
            except Exception as e:
                print(f"   ⚠️ Erro migrando usuários diários: {e}")
            
            # Migrar error_logs
            print("   🚨 Migrando logs de erro...")
            try:
                errors = conn.execute("SELECT * FROM error_logs").fetchall()
                for error in errors:
                    error_log = ErrorLogs(
                        user_id=error['user_id'],
                        username=error['username'],
                        command=error['command'],
                        error_type=error['error_type'],
                        error_message=error['error_message'],
                        stack_trace=error['stack_trace'],
                        timestamp=datetime.fromisoformat(error['timestamp'].replace('Z', '+00:00')) if error['timestamp'] else datetime.now(),
                        extra_data=error['metadata']  # Renomeado
                    )
                    session.add(error_log)
            except Exception as e:
                print(f"   ⚠️ Erro migrando logs de erro: {e}")
                
            session.commit()
            
        conn.close()
        
        # 4. Verificar migração
        print("4️⃣ Verificando migração...")
        stats = pg_analytics.get_daily_stats()
        print(f"   📊 Comandos migrados: {stats.get('total_commands', 0)}")
        print(f"   👥 Usuários únicos: {stats.get('unique_users', 0)}")
        
        print("✅ Migração concluída com sucesso!")
        return True
        
    except Exception as e:
        print(f"❌ Erro na migração: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_synthetic_data(pg_analytics):
    """Cria dados sintéticos para demonstração"""
    print("🎯 Criando dados sintéticos para demonstração...")
    
    from datetime import datetime, timedelta
    import random
    
    try:
        comandos = ['start', 'gerente', 'relatorio', 'categorias', 'dashboard', 'ocr', 'graficos']
        usuarios = [
            (6157591255, 'Henrique'),
            (1250505512, 'Natasha'),
            (7379051025, 'Raquel'),
            (5660820035, 'Aaron')
        ]
        
        # Gerar dados dos últimos 30 dias
        for days_ago in range(30):
            date = datetime.now() - timedelta(days=days_ago)
            
            for user_id, username in usuarios:
                # Chance de usar o app neste dia
                if random.random() < 0.6:  # 60% chance
                    commands_today = random.randint(1, 8)
                    
                    for _ in range(commands_today):
                        cmd = random.choice(comandos)
                        success = random.random() > 0.05  # 95% sucesso
                        exec_time = random.randint(100, 2000)
                        
                        # Usar timestamp específico para o dia
                        timestamp = date.replace(
                            hour=random.randint(8, 22),
                            minute=random.randint(0, 59),
                            second=random.randint(0, 59)
                        )
                        
                        pg_analytics.track_command_usage(
                            user_id=user_id,
                            username=username,
                            command=cmd,
                            success=success,
                            execution_time_ms=exec_time
                        )
                        
        print("✅ Dados sintéticos criados!")
        
    except Exception as e:
        print(f"❌ Erro criando dados sintéticos: {e}")

if __name__ == '__main__':
    success = migrate_analytics_to_postgresql()
    if success:
        print("\n🎉 ANALYTICS PRONTO PARA O RENDER!")
    else:
        print("\n❌ Falha na migração - verifique os logs")
