#!/bin/bash

# 🎯 MAESTROFIN - LIMPEZA COMPLETA DO WORKSPACE
# Use este script para finalizar o trabalho e manter o workspace limpo

echo ""
echo "🎼 =========================================="
echo "    MAESTROFIN - FINALIZANDO TRABALHO"
echo "=========================================="
echo ""

# Parar todos os processos do MaestroFin
echo "🛑 1. Parando processos do MaestroFin..."
pkill -f bot.py 2>/dev/null || true
pkill -f dashboard 2>/dev/null || true
pkill -f analytics 2>/dev/null || true

# Limpeza de arquivos temporários e desnecessários do MaestroFin
echo "🧹 2. Limpando arquivos temporários..."
rm -rf __pycache__ .pytest_cache *.pyc .coverage
rm -rf .vscode/ .history/ *.code-workspace
rm -f *.log dashboard_handler.log
rm -f maestrofin_local.db analytics.db
rm -rf test_* *_test.py *test*.py
rm -f *_backup.py *.backup
rm -f analytics/dashboard_simple.py analytics/dashboard_app_fixed.py 2>/dev/null || true

# Limpeza do ambiente virtual se necessário
echo "🔄 3. Verificando ambiente virtual..."
if [ -d ".venv" ]; then
    echo "   ✅ Ambiente virtual mantido"
else
    echo "   ⚠️ Ambiente virtual não encontrado"
fi

# Status do Git
echo "📋 4. Status do repositório:"
git status --short

echo ""
echo "💾 O que você quer fazer com as alterações?"
echo "1) Salvar progresso (commit e push)"
echo "2) Finalizar funcionalidade (merge na main)"
echo "3) Descartar tudo (reset limpo)"
echo "4) Apenas limpar (manter alterações locais)"
echo ""
read -p "Escolha (1-4): " opcao

case $opcao in
    1)
        echo "💾 Salvando progresso..."
        read -p "Descreva o que foi desenvolvido: " mensagem
        git add -A
        git commit -m "🚧 WIP: $mensagem"
        git push -u origin $(git branch --show-current)
        echo "✅ Progresso salvo!"
        ;;
    2)
        echo "🎉 Finalizando funcionalidade..."
        read -p "Descreva a funcionalidade completa: " mensagem
        current_branch=$(git branch --show-current)
        git add -A
        git commit -m "✨ $mensagem"
        git checkout main
        git merge $current_branch --no-ff -m "🔀 Merge: $mensagem"
        git push origin main
        git branch -d $current_branch
        echo "✅ Funcionalidade finalizada e integrada na main!"
        ;;
    3)
        echo "🗑️ Descartando alterações..."
        git checkout main
        current_branch=$(git branch --show-current)
        if [ "$current_branch" != "main" ]; then
            git branch -D $current_branch 2>/dev/null || true
        fi
        git reset --hard HEAD
        git clean -fd
        echo "✅ Workspace resetado para estado limpo!"
        ;;
    4)
        echo "🧹 Apenas limpando arquivos temporários..."
        echo "✅ Limpeza concluída! Alterações mantidas."
        ;;
    *)
        echo "❌ Opção inválida"
        exit 1
        ;;
esac

echo ""
echo "🎼 MAESTROFIN - TRABALHO FINALIZADO!"
echo "📁 Workspace: LIMPO"
echo "🔄 Processos: PARADOS"
echo "💡 Para iniciar amanhã: python bot.py ou ./novo_desenvolvimento.sh"
echo ""
