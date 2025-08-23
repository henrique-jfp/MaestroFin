#!/bin/bash

echo "🧹 LIMPEZA DEFINITIVA DO WORKSPACE"
echo "================================="

# 1. Limpar cache do Git
echo "1️⃣ Limpando cache do Git..."
git rm -r --cached . 2>/dev/null || true
git add .
git status

# 2. Remover arquivos temporários e configurações VSCode
echo "2️⃣ Removendo arquivos temporários..."
rm -rf .vscode/
rm -rf __pycache__/
rm -rf .pytest_cache/
rm -rf *.pyc
rm -rf .coverage
rm -rf analytics.db

# 3. Limpar histórico do VSCode
echo "3️⃣ Limpando histórico do VSCode..."
rm -rf .history/
rm -rf *.code-workspace

# 4. Reset do Git se necessário
echo "4️⃣ Status final do Git:"
git status

echo ""
echo "✅ LIMPEZA CONCLUÍDA!"
echo "💡 Agora feche COMPLETAMENTE o VSCode e reabra o projeto."
echo "💡 Use sempre este script antes de fechar o projeto."
