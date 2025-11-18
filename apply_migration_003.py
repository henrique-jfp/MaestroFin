#!/usr/bin/env python3
"""
📈 Migration 003 - Investments System
Aplica a migration que cria tabelas de investimentos
"""

import os
import sys
import psycopg2
from psycopg2 import sql

def apply_migration():
    """Aplica migration 003"""
    
    # Obter DATABASE_URL do ambiente
    database_url = os.environ.get('DATABASE_URL')
    
    if not database_url:
        print("❌ DATABASE_URL não encontrada no ambiente!")
        print("💡 Para testar localmente, configure: export DATABASE_URL='postgresql://user:pass@localhost/dbname'")
        sys.exit(1)
    
    # Ler o SQL da migration
    migration_file = 'migrations/003_create_investments_table.sql'
    
    try:
        with open(migration_file, 'r', encoding='utf-8') as f:
            migration_sql = f.read()
    except FileNotFoundError:
        print(f"❌ Arquivo {migration_file} não encontrado!")
        sys.exit(1)
    
    # Conectar ao banco
    print(f"🔌 Conectando ao banco de dados...")
    
    try:
        conn = psycopg2.connect(database_url)
        conn.autocommit = False  # Usar transação manual
        cursor = conn.cursor()
        
        print(f"✅ Conectado com sucesso!")
        print(f"\n📋 Aplicando migration 003...")
        
        # Executar migration
        cursor.execute(migration_sql)
        
        # Commit
        conn.commit()
        
        print(f"\n✅ Migration 003 aplicada com sucesso!")
        print(f"\n📊 Tabelas criadas:")
        print(f"   • investments (investimentos)")
        print(f"   • investment_snapshots (histórico de valores)")
        print(f"   • investment_goals (metas de investimento)")
        print(f"   • patrimony_snapshots (snapshots mensais de patrimônio)")
        
        # Verificar se as tabelas foram criadas
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('investments', 'investment_snapshots', 'investment_goals', 'patrimony_snapshots')
            ORDER BY table_name;
        """)
        
        tables = cursor.fetchall()
        
        print(f"\n🔍 Verificação:")
        if len(tables) == 4:
            print(f"   ✅ Todas as 4 tabelas foram criadas com sucesso!")
            for table in tables:
                print(f"      • {table[0]}")
        else:
            print(f"   ⚠️  Apenas {len(tables)} tabelas foram encontradas:")
            for table in tables:
                print(f"      • {table[0]}")
        
        cursor.close()
        conn.close()
        
        print(f"\n🎉 Migration concluída! O sistema de investimentos está pronto para uso.")
        
    except psycopg2.Error as e:
        print(f"\n❌ Erro ao aplicar migration:")
        print(f"   {e}")
        
        if conn:
            conn.rollback()
            conn.close()
        
        sys.exit(1)
    
    except Exception as e:
        print(f"\n❌ Erro inesperado:")
        print(f"   {e}")
        
        if conn:
            conn.rollback()
            conn.close()
        
        sys.exit(1)

if __name__ == "__main__":
    print("=" * 60)
    print("📈 MAESTRO FINANCEIRO - Migration 003")
    print("   Investments & Patrimony System")
    print("=" * 60)
    print()
    
    apply_migration()
