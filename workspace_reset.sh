#!/bin/bash

# 🚨 RESET COMPLETO - Para casos de emergência
# Quando der tudo errado e você quiser voltar para o estado LIMPO

echo ""
echo "🚨 =========================================="
echo "    RESET COMPLETO DO WORKSPACE"
echo "=========================================="
echo ""

echo "⚠️  ATENÇÃO: Isso vai APAGAR TUDO que não está commitado!"
echo "✅ Vai voltar exatamente para o estado da main limpa"
echo ""
read -p "Tem certeza? Digite 'RESET' para confirmar: " confirmacao

if [ "$confirmacao" != "RESET" ]; then
    echo "❌ Operação cancelada"
    exit 1
fi

echo ""
echo "🔄 Executando reset completo..."

# 1. Voltar para main
git checkout main 2>/dev/null || true

# 2. Apagar todos os branches locais exceto main
git branch | grep -v "main" | xargs -r git branch -D

# 3. Puxar versão mais recente da main
git fetch origin
git reset --hard origin/main

# 4. Limpar tudo
git clean -fdx

# 5. Remover arquivos do VSCode
rm -rf .vscode/ .history/ *.code-workspace
rm -rf __pycache__ .pytest_cache *.pyc .coverage

echo ""
echo "✅ RESET COMPLETO FINALIZADO!"
echo "📁 Workspace: 100% LIMPO"
echo "🌿 Branch: main (versão limpa)"
echo ""
echo "💡 Para iniciar novo desenvolvimento: ./novo_desenvolvimento.sh"
echo ""
