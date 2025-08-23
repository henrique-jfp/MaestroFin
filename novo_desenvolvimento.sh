#!/bin/bash

# 🎯 WORKFLOW PROFISSIONAL - NOVO BRANCH
# Use este script para iniciar um novo desenvolvimento SEMPRE

echo ""
echo "🎯 =========================================="
echo "    INICIANDO NOVO DESENVOLVIMENTO"
echo "=========================================="
echo ""

# 1. Garantir que estamos na main limpa
echo "📍 1. Voltando para branch main limpa..."
git checkout main
git pull origin main

# 2. Limpar qualquer lixo local
echo "🧹 2. Limpando workspace..."
git clean -fd
git reset --hard HEAD

# 3. Criar novo branch para desenvolvimento
echo "🌿 3. Qual funcionalidade vai desenvolver?"
read -p "Nome do branch (ex: nova-funcionalidade): " branch_name

if [ -z "$branch_name" ]; then
    branch_name="desenvolvimento-$(date +%Y%m%d-%H%M)"
fi

git checkout -b "$branch_name"

echo ""
echo "✅ PRONTO PARA TRABALHAR!"
echo "📁 Workspace: LIMPO"
echo "🌿 Branch: $branch_name"
echo "🚀 Pode começar a desenvolver!"
echo ""
echo "💡 Quando terminar use: ./finalizar_trabalho.sh"
echo ""
