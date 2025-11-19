#!/usr/bin/env zsh
set -euo pipefail

# Script para commitar e dar push das alterações do relatório
# Revise antes de executar.

# Caminho relativo ao repositório (execute a partir da raiz do projeto)
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

echo "Status atual do git:"
git status --porcelain

echo
read "-q?Deseja continuar e commitar as alterações relacionadas ao relatório? (y/N): " REPLY
if [[ "$REPLY" != "y" && "$REPLY" != "Y" ]]; then
  echo "Abortando. Nenhuma alteração foi enviada."
  exit 1
fi

# Arquivos que foram alterados pelo ajuste do gerador de PDF
git add gerente_financeiro/pdf_generator.py
# optional: arquivos auxiliares que também foram alterados
git add gerente_financeiro/relatorio_handler.py || true
git add templates/relatorio_clean.html || true
git add gerente_financeiro/services.py || true

COMMIT_MSG="chore(relatorio): melhorar aparência do PDF (tipografia, sombras, bordas, cabeçalho/rodapé)"

echo "Comitando com a mensagem: $COMMIT_MSG"
git commit -m "$COMMIT_MSG"

# Push para a branch atual
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)

echo "Fazendo push para origin/$CURRENT_BRANCH..."
git push origin "$CURRENT_BRANCH"

echo "Push concluído."

# Mostrar último commit
git --no-pager log -1 --stat
