#!/bin/bash
# 🧹 Quick Workspace Cleaner - Limpeza rápida e segura

echo "🧹 MAESTROFIN QUICK CLEANER"
echo "=" * 50

# Verificar se está no diretório correto
if [ ! -f "bot.py" ]; then
    echo "❌ Execute no diretório raiz do MaestroFin!"
    exit 1
fi

echo "🔍 Procurando arquivos para limpar..."

# Contadores
removed_count=0

# ❌ Remover arquivos de documentação obsoletos
echo "📄 Removendo documentação obsoleta..."
for file in WEBHOOK_*.md DEBUG_*.md GUIA_*.md WORKFLOW.md ARQUIVOS_*.md; do
    if [ -f "$file" ]; then
        echo "   ❌ $file"
        rm "$file"
        ((removed_count++))
    fi
done

# ❌ Remover launchers obsoletos
echo "🚀 Removendo launchers obsoletos..."
for file in bot_launcher.py simple_bot_launcher.py bot_render_launcher.py webhook_launcher.py; do
    if [ -f "$file" ]; then
        echo "   ❌ $file"
        rm "$file"
        ((removed_count++))
    fi
done

# ❌ Remover configurações antigas
echo "⚙️ Removendo configurações antigas..."
for file in render.yaml runtime.txt advanced_config.py; do
    if [ -f "$file" ]; then
        echo "   ❌ $file"
        rm "$file"
        ((removed_count++))
    fi
done

# ❌ Remover arquivos de teste
echo "🧪 Removendo arquivos de teste..."
for file in test_*.py exemplo_*.py demo_*.py; do
    if [ -f "$file" ]; then
        echo "   ❌ $file"
        rm "$file"
        ((removed_count++))
    fi
done

# ❌ Remover backups e temporários
echo "🗑️ Removendo backups e temporários..."
for file in *.backup *.bak *.tmp *.temp *_backup.py *_old.py; do
    if [ -f "$file" ]; then
        echo "   ❌ $file"
        rm "$file"
        ((removed_count++))
    fi
done

# ❌ Remover logs antigos
echo "📋 Removendo logs antigos..."
for file in *.log dashboard_handler.log; do
    if [ -f "$file" ]; then
        echo "   ❌ $file"
        rm "$file"
        ((removed_count++))
    fi
done

# 🧹 Limpar __pycache__ (apenas .pyc, manter diretórios)
echo "🗂️ Limpando cache Python..."
find . -name "*.pyc" -type f -delete 2>/dev/null
pyc_count=$(find . -name "*.pyc" -type f 2>/dev/null | wc -l)
echo "   🧹 Removidos ~$pyc_count arquivos .pyc"

# 📖 Remover READMEs duplicados (manter apenas o principal)
echo "📖 Removendo READMEs duplicados..."
find . -name "README.md" -not -path "./README.md" -type f -delete 2>/dev/null

echo ""
echo "✅ LIMPEZA CONCLUÍDA!"
echo "📊 Total removido: $removed_count arquivos"
echo "🎯 Workspace limpo e organizado!"
