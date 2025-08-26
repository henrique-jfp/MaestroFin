#!/bin/bash
# 🧹 MAESTRO CLEANER - Menu de Limpeza Inteligente

clear
echo "🧹 MAESTROFIN WORKSPACE CLEANER"
echo "=================================="
echo ""
echo "Escolha o tipo de limpeza:"
echo ""
echo "1) 🚀 Quick Clean    - Limpeza rápida e básica"
echo "2) 🔍 Smart Clean    - Limpeza inteligente com preview"
echo "3) 📋 Preview Only   - Apenas mostrar o que seria removido"
echo "4) ❌ Cancelar"
echo ""
echo -n "Opção [1-4]: "
read option

case $option in
    1)
        echo ""
        echo "🚀 EXECUTANDO QUICK CLEAN..."
        echo "=============================="
        ./quick_clean.sh
        ;;
    2)
        echo ""
        echo "🔍 EXECUTANDO SMART CLEAN..."
        echo "=============================="
        python3 clean_workspace.py
        ;;
    3)
        echo ""
        echo "📋 PREVIEW MODE..."
        echo "=================="
        python3 -c "
from clean_workspace import WorkspaceCleaner
cleaner = WorkspaceCleaner()
cleaner.show_preview()
print('\n🔍 Use opção 2 para executar a limpeza.')
"
        ;;
    4)
        echo "❌ Operação cancelada."
        exit 0
        ;;
    *)
        echo "❌ Opção inválida!"
        exit 1
        ;;
esac

echo ""
echo "✅ Processo concluído!"
echo "🎯 Para fazer commit das mudanças:"
echo "   git add -A && git commit -m '🧹 Workspace cleaned' && git push"
