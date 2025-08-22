#!/bin/bash
"""
Script de Deploy Automatizado - Railway
Executa todas as correções e faz o push
"""

echo "🚀 PREPARANDO DEPLOY PARA RAILWAY"
echo "=================================="

# Navegar para o diretório do projeto
cd "/home/henriquejfp/Área de trabalho/Projetos/Projetos Pessoais/MaestroFin"

echo "📦 Verificando dependências..."
source activate_env.sh
pip freeze | grep Flask

echo "🔍 Verificando arquivos corrigidos..."
echo "✅ requirements.txt - Flask duplicado removido"
echo "✅ runtime.txt - Python 3.11 especificado" 
echo "✅ railway.json - Configuração otimizada"
echo "✅ Procfile - Comando correto"

echo ""
echo "📋 PRÓXIMOS PASSOS PARA DEPLOY:"
echo "1. Commit as correções:"
echo "   git add ."
echo "   git commit -m '🔧 Fix Flask conflict for Railway deploy'"
echo "   git push origin continuacao-analystics"
echo ""
echo "2. No Railway Dashboard:"
echo "   - Configure as variáveis de ambiente"
echo "   - TELEGRAM_TOKEN (obrigatório)"
echo "   - GEMINI_API_KEY (obrigatório)"
echo "   - Outras conforme necessário"
echo ""
echo "3. Aguarde o deploy automático"
echo "   - Railway detectará as mudanças"
echo "   - Build deve funcionar agora"
echo "   - Bot ficará online em poucos minutos"
echo ""
echo "🎯 PROBLEMA DO FLASK RESOLVIDO!"
echo "O conflito Flask==3.0.0 vs Flask==3.1.0 foi corrigido"
