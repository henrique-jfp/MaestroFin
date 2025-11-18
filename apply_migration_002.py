#!/usr/bin/env python3
"""
Script para aplicar migration 002: Criar tabelas Open Finance/Pluggy
Uso: python apply_migration_002.py
"""

import os
import sys
import logging
from pathlib import Path

# Adicionar diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent))

from database.database import engine
from sqlalchemy import text

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def apply_migration():
    """Aplica a migration 002 - Tabelas Pluggy"""
    
    migration_file = Path(__file__).parent / "migrations" / "002_create_pluggy_tables.sql"
    
    if not migration_file.exists():
        logger.error(f"❌ Arquivo de migration não encontrado: {migration_file}")
        return False
    
    logger.info("🚀 Iniciando aplicação da migration 002: Tabelas Open Finance/Pluggy")
    
    try:
        # Ler SQL
        with open(migration_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        logger.info("📄 Migration SQL carregada com sucesso")
        
        # Executar SQL
        with engine.begin() as conn:
            # Separar por blocos (cada CREATE TABLE é executado separadamente)
            statements = sql_content.split(';')
            
            for idx, statement in enumerate(statements, 1):
                statement = statement.strip()
                if statement and not statement.startswith('--'):
                    try:
                        conn.execute(text(statement))
                        logger.info(f"✅ Statement {idx} executado com sucesso")
                    except Exception as e:
                        # Ignorar erros de "já existe"
                        if "already exists" in str(e).lower():
                            logger.info(f"ℹ️  Statement {idx} pulado (já existe)")
                        else:
                            raise
        
        logger.info("🎉 Migration 002 aplicada com sucesso!")
        logger.info("📊 Tabelas criadas:")
        logger.info("   - pluggy_items (conexões bancárias)")
        logger.info("   - pluggy_accounts (contas)")
        logger.info("   - pluggy_transactions (transações)")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao aplicar migration: {e}", exc_info=True)
        return False

def verify_tables():
    """Verifica se as tabelas foram criadas"""
    logger.info("🔍 Verificando tabelas criadas...")
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_name IN ('pluggy_items', 'pluggy_accounts', 'pluggy_transactions')
                ORDER BY table_name
            """))
            
            tables = [row[0] for row in result]
            
            if len(tables) == 3:
                logger.info(f"✅ Todas as tabelas verificadas: {', '.join(tables)}")
                return True
            else:
                logger.warning(f"⚠️  Apenas {len(tables)}/3 tabelas encontradas: {', '.join(tables)}")
                return False
                
    except Exception as e:
        logger.error(f"❌ Erro ao verificar tabelas: {e}")
        return False

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("MIGRATION 002: TABELAS OPEN FINANCE/PLUGGY")
    logger.info("=" * 60)
    
    if not engine:
        logger.error("❌ Engine do banco de dados não inicializada!")
        sys.exit(1)
    
    # Aplicar migration
    if apply_migration():
        # Verificar resultado
        if verify_tables():
            logger.info("✅ Migration concluída com sucesso!")
            sys.exit(0)
        else:
            logger.error("❌ Migration aplicada mas verificação falhou")
            sys.exit(1)
    else:
        logger.error("❌ Falha ao aplicar migration")
        sys.exit(1)
