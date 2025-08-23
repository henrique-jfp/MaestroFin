#!/bin/bash
# RESET COMPLETO - Use apenas em casos extremos

echo "⚠️  RESET COMPLETO DO PROJETO"
echo "============================="
read -p "Tem certeza? Isso vai limpar TUDO! (y/N): " confirm

if [[ $confirm == [yY] ]]; then
    echo "🔥 Executando reset completo..."
    
    # Reset do Git mantendo apenas arquivos rastreados
    git reset --hard HEAD
    git clean -fd
    
    # Limpar completamente o cache
    git rm -r --cached . 2>/dev/null || true
    git add .
    
    # Remover tudo que não deveria estar no Git  
    rm -rf .vscode/ __pycache__/ .pytest_cache/ *.pyc .coverage analytics.db
    rm -rf .history/ *.code-workspace
    
    echo "✅ Reset completo finalizado!"
    echo "💡 Feche o VSCode e reabra o projeto."
else
    echo "❌ Operação cancelada."
fi
