#!/bin/bash

# 🎯 WORKFLOW PROFISSIONAL - FINALIZAR TRABALHO
# Use este script ao final do dia SEMPRE

echo ""
echo "🎯 =========================================="
echo "    FINALIZANDO TRABALHO DO DIA"
echo "=========================================="
echo ""

# Mostrar o que foi modificado
echo "📋 Arquivos modificados hoje:"
git status --short

echo ""
echo "💾 O que você quer fazer?"
echo "1) Salvar progresso (commit no branch atual)"
echo "2) Finalizar funcionalidade (merge na main)"
echo "3) Descartar tudo (voltar para main limpa)"
echo ""
read -p "Escolha (1-3): " opcao

case $opcao in
    1)
        echo "💾 Salvando progresso..."
        read -p "Descreva o que fez hoje: " mensagem
        git add -A
        git commit -m "🚧 WIP: $mensagem"
        git push -u origin $(git branch --show-current)
        echo "✅ Progresso salvo! Amanhã continue com: git checkout $(git branch --show-current)"
        ;;
    2)
        echo "🎉 Finalizando funcionalidade..."
        read -p "Descreva a funcionalidade completa: " mensagem
        git add -A
        git commit -m "✨ $mensagem"
        git checkout main
        git merge $(git branch --show-current) --no-ff
        git push origin main
        git branch -d $(git branch --show-current)
        echo "✅ Funcionalidade finalizada e integrada na main!"
        ;;
    3)
        echo "🗑️ Descartando alterações..."
        git checkout main
        git branch -D $(git branch --show-current) 2>/dev/null || true
        git reset --hard HEAD
        git clean -fd
        echo "✅ Workspace voltou para estado limpo!"
        ;;
    *)
        echo "❌ Opção inválida"
        exit 1
        ;;
esac

# Limpeza final sempre
echo ""
echo "🧹 Limpeza final..."
rm -rf __pycache__ .pytest_cache *.pyc .coverage
rm -rf .vscode/ .history/ *.code-workspace

echo ""
echo "✅ TRABALHO FINALIZADO!"
echo "💡 Amanhã use: ./novo_desenvolvimento.sh"
echo ""
