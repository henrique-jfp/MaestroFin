#!/usr/bin/env python3
"""
scripts/cleanup_openfinance.py

Utilitário seguro para fazer backup e limpar importações Open Finance

Modo de uso:
  # Dry-run (apenas mostra contagens)
  python scripts/cleanup_openfinance.py --dry-run

  # Backup e reset (interativo)
  python scripts/cleanup_openfinance.py

  # Executa sem prompt (FORÇAR) - use com cuidado
  python scripts/cleanup_openfinance.py --yes

Este script cria uma tabela de backup com os lançamentos gerados a partir de
`pluggy_transactions` e depois oferece opções para deletar os lançamentos
e resetar as flags em `pluggy_transactions` para permitir reconexão/reimport.
"""
from datetime import datetime
import argparse
import sys
import logging

from database.database import get_db

logger = logging.getLogger("cleanup_openfinance")
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


def main(dry_run: bool = False, assume_yes: bool = False):
    db = next(get_db())
    try:
        # Contar transações que têm link para lancamento
        res = db.execute("SELECT COUNT(*) FROM pluggy_transactions WHERE id_lancamento IS NOT NULL")
        count_linked = int(res.scalar() or 0)

        res2 = db.execute("SELECT COUNT(*) FROM pluggy_transactions WHERE imported_to_lancamento = true")
        count_imported_flag = int(res2.scalar() or 0)

        logger.info(f"Transações pluggy com id_lancamento: {count_linked}")
        logger.info(f"Transações pluggy com imported_to_lancamento = true: {count_imported_flag}")

        if dry_run:
            logger.info("Dry-run selecionado — nenhuma alteração será feita.")
            return 0

        if not assume_yes:
            confirm = input("Continuar e fazer backup + limpeza? (type YES to continue): ")
            if confirm.strip() != 'YES':
                logger.info("Operação cancelada pelo usuário.")
                return 0

        # 1) Criar backup dos lançamentos vinculados
        ts = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        backup_table = f"backup_lancamentos_openfinance_{ts}"
        logger.info(f"Criando tabela de backup: {backup_table}")
        db.execute(f"CREATE TABLE {backup_table} AS SELECT l.* FROM lancamentos l WHERE l.id IN (SELECT pt.id_lancamento FROM pluggy_transactions pt WHERE pt.id_lancamento IS NOT NULL);")
        db.commit()
        logger.info("Backup criado com sucesso.")

        # 2) Deletar lançamentos criados a partir de pluggy (opcional)
        logger.info("Deletando lançamentos vinculados a pluggy_transactions (isso é irreversível se você não tiver backup).")
        db.execute("DELETE FROM lancamentos WHERE id IN (SELECT id_lancamento FROM pluggy_transactions WHERE id_lancamento IS NOT NULL);")
        # 3) Resetar flags em pluggy_transactions para permitir reimport
        db.execute("UPDATE pluggy_transactions SET imported_to_lancamento = false, id_lancamento = NULL;")
        db.commit()

        logger.info("Limpeza concluída. Agora você pode reconectar e reimportar as transações.")
        logger.info(f"Backup mantido na tabela: {backup_table}")
        return 0

    except Exception as e:
        logger.error(f"Erro durante cleanup: {e}")
        db.rollback()
        return 2
    finally:
        db.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Backup & cleanup de importações Open Finance')
    parser.add_argument('--dry-run', action='store_true', help='Mostrar contagens sem alterar o banco')
    parser.add_argument('--yes', action='store_true', help='Assume YES para confirmar operações destrutivas')
    args = parser.parse_args()
    sys.exit(main(dry_run=args.dry_run, assume_yes=args.yes))
