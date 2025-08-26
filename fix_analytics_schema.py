#!/usr/bin/env python3
"""
🔧 Fix Analytics Schema - Corrige problema de integer out of range
Migra colunas INTEGER para BIGINT para suportar IDs do Telegram
"""

import os
import logging
import psycopg2
from sqlalchemy import create_engine, text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_analytics_schema():
    """Corrige schema do analytics para usar BIGINT"""
    try:
        # Conectar ao banco
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            logger.error("❌ DATABASE_URL não configurado")
            return False
            
        logger.info("🔧 Conectando ao PostgreSQL...")
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            # Começar transação
            trans = conn.begin()
            
            try:
                logger.info("🔄 Verificando tabelas existentes...")
                
                # Verificar se as tabelas existem
                result = conn.execute(text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name LIKE 'analytics_%'
                """))
                
                existing_tables = [row[0] for row in result.fetchall()]
                logger.info(f"📋 Tabelas encontradas: {existing_tables}")
                
                if not existing_tables:
                    logger.info("✅ Nenhuma tabela analytics encontrada - schema será criado automaticamente")
                    trans.commit()
                    return True
                
                # ✅ ESTRATÉGIA: Recriar tabelas com schema correto
                logger.info("🗑️ Removendo tabelas antigas...")
                
                # Dropar tabelas na ordem correta (considerando foreign keys)
                tables_to_drop = [
                    'analytics_command_usage',
                    'analytics_daily_users', 
                    'analytics_error_logs'
                ]
                
                for table in tables_to_drop:
                    if table in existing_tables:
                        logger.info(f"🗑️ Dropando tabela {table}...")
                        conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
                
                logger.info("✅ Tabelas antigas removidas")
                
                # As novas tabelas serão criadas automaticamente pelo SQLAlchemy
                # com o schema correto (BIGINT)
                trans.commit()
                
                logger.info("🎉 Schema corrigido com sucesso!")
                logger.info("📝 Novas tabelas serão criadas automaticamente com BIGINT")
                
                return True
                
            except Exception as e:
                trans.rollback()
                logger.error(f"❌ Erro na migração: {e}")
                return False
                
    except Exception as e:
        logger.error(f"❌ Erro ao conectar: {e}")
        return False

def test_new_schema():
    """Testa o novo schema"""
    try:
        logger.info("🧪 Testando novo schema...")
        
        # Importar analytics para criar tabelas
        from analytics.bot_analytics_postgresql import get_analytics
        analytics = get_analytics()
        
        # Testar inserção com ID grande do Telegram
        test_user_id = 6157591255  # ID real do Telegram
        
        logger.info(f"✅ Testando inserção com user_id: {test_user_id}")
        
        # Simular tracking de comando
        success = analytics.track_command_usage(
            user_id=test_user_id,
            username="TestUser",
            command="test_bigint",
            success=True,
            execution_time_ms=100
        )
        
        if success:
            logger.info("🎉 Teste de inserção bem-sucedido!")
            return True
        else:
            logger.error("❌ Teste de inserção falhou")
            return False
            
    except Exception as e:
        logger.error(f"❌ Erro no teste: {e}")
        return False

def main():
    """Função principal"""
    logger.info("🚀 Iniciando correção do schema analytics...")
    
    # Corrigir schema
    if fix_analytics_schema():
        logger.info("✅ Schema corrigido!")
        
        # Testar novo schema
        if test_new_schema():
            logger.info("🎉 Correção concluída com sucesso!")
        else:
            logger.warning("⚠️ Schema corrigido mas teste falhou")
    else:
        logger.error("❌ Falha na correção do schema")

if __name__ == '__main__':
    main()
