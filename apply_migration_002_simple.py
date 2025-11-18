#!/usr/bin/env python3
"""
Script simplificado para aplicar migration via psycopg2 (sem SQLAlchemy)
"""

import os
import psycopg2
from pathlib import Path

# Pegar DATABASE_URL do ambiente
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("❌ DATABASE_URL não configurada")
    exit(1)

migration_file = Path(__file__).parent / "migrations" / "002_create_pluggy_tables.sql"

print("🚀 Aplicando migration 002: Tabelas Open Finance/Pluggy")

try:
    # Ler SQL
    with open(migration_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    print("📄 Migration SQL carregada")
    
    # Conectar ao banco
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    # Executar SQL
    cursor.execute(sql_content)
    conn.commit()
    
    print("✅ Migration aplicada com sucesso!")
    
    # Verificar tabelas
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_name IN ('pluggy_items', 'pluggy_accounts', 'pluggy_transactions')
        ORDER BY table_name
    """)
    
    tables = cursor.fetchall()
    print(f"📊 Tabelas criadas: {', '.join([t[0] for t in tables])}")
    
    cursor.close()
    conn.close()
    
    print("🎉 Concluído!")
    
except Exception as e:
    print(f"❌ Erro: {e}")
    exit(1)
