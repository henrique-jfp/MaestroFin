# migrate.py
"""
Script para migração de dados do SQLite para PostgreSQL
"""
import sqlite3
import psycopg2
import os
from dotenv import load_dotenv
import logging
from datetime import datetime

load_dotenv()

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseMigrator:
    def __init__(self):
        self.sqlite_path = "./maestro_financeiro.db"
        self.postgres_url = os.getenv("POSTGRES_URL")  # URL do PostgreSQL de produção
        
    def connect_sqlite(self):
        """Conecta ao SQLite local"""
        try:
            conn = sqlite3.connect(self.sqlite_path)
            conn.row_factory = sqlite3.Row  # Para acessar colunas por nome
            return conn
        except Exception as e:
            logger.error(f"Erro ao conectar SQLite: {e}")
            return None
    
    def connect_postgres(self):
        """Conecta ao PostgreSQL de produção"""
        try:
            conn = psycopg2.connect(self.postgres_url)
            return conn
        except Exception as e:
            logger.error(f"Erro ao conectar PostgreSQL: {e}")
            return None
    
    def migrate_table(self, table_name, columns_mapping=None):
        """
        Migra uma tabela específica do SQLite para PostgreSQL
        """
        sqlite_conn = self.connect_sqlite()
        postgres_conn = self.connect_postgres()
        
        if not sqlite_conn or not postgres_conn:
            logger.error("Falha na conexão com os bancos")
            return False
        
        try:
            # Ler dados do SQLite
            sqlite_cursor = sqlite_conn.cursor()
            sqlite_cursor.execute(f"SELECT * FROM {table_name}")
            rows = sqlite_cursor.fetchall()
            
            if not rows:
                logger.info(f"Tabela {table_name} está vazia, pulando...")
                return True
            
            # Preparar inserção no PostgreSQL
            postgres_cursor = postgres_conn.cursor()
            
            # Obter nomes das colunas
            column_names = [description[0] for description in sqlite_cursor.description]
            
            # Criar placeholders para inserção
            placeholders = ", ".join(["%s"] * len(column_names))
            columns_str = ", ".join(column_names)
            
            # Query de inserção
            insert_query = f"""
                INSERT INTO {table_name} ({columns_str}) 
                VALUES ({placeholders})
                ON CONFLICT DO NOTHING
            """
            
            # Inserir dados
            for row in rows:
                postgres_cursor.execute(insert_query, tuple(row))
            
            postgres_conn.commit()
            logger.info(f"✅ Migração da tabela {table_name} concluída: {len(rows)} registros")
            return True
            
        except Exception as e:
            logger.error(f"Erro na migração da tabela {table_name}: {e}")
            if postgres_conn:
                postgres_conn.rollback()
            return False
            
        finally:
            if sqlite_conn:
                sqlite_conn.close()
            if postgres_conn:
                postgres_conn.close()
    
    def full_migration(self):
        """
        Executa migração completa de todas as tabelas
        """
        tables = [
            "usuarios",
            "contas", 
            "categorias",
            "subcategorias",
            "lancamentos",
            "objetivos",
            "agendamentos",
            "chat_history"
        ]
        
        logger.info("🚀 Iniciando migração completa...")
        
        success_count = 0
        for table in tables:
            if self.migrate_table(table):
                success_count += 1
        
        logger.info(f"✅ Migração concluída: {success_count}/{len(tables)} tabelas migradas")
        return success_count == len(tables)
    
    def backup_sqlite(self):
        """
        Cria backup do SQLite antes da migração
        """
        if not os.path.exists(self.sqlite_path):
            logger.warning("Arquivo SQLite não encontrado para backup")
            return False
        
        backup_name = f"maestro_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        
        try:
            import shutil
            shutil.copy2(self.sqlite_path, backup_name)
            logger.info(f"✅ Backup criado: {backup_name}")
            return True
        except Exception as e:
            logger.error(f"Erro ao criar backup: {e}")
            return False

def main():
    """
    Executa o processo de migração
    """
    migrator = DatabaseMigrator()
    
    print("🎼 Maestro Financeiro - Migração de Dados")
    print("=" * 50)
    
    # Criar backup
    print("📦 Criando backup do SQLite...")
    migrator.backup_sqlite()
    
    # Confirmar migração
    confirm = input("Deseja prosseguir com a migração? (y/n): ")
    if confirm.lower() != 'y':
        print("❌ Migração cancelada")
        return
    
    # Executar migração
    success = migrator.full_migration()
    
    if success:
        print("\n🎉 Migração concluída com sucesso!")
        print("Agora você pode:")
        print("1. Alterar DATABASE_URL no .env para o PostgreSQL")
        print("2. Reiniciar a aplicação")
        print("3. Verificar se tudo está funcionando")
    else:
        print("\n❌ Migração falhou. Verifique os logs acima.")

if __name__ == "__main__":
    main()
