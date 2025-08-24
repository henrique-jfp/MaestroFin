#!/bin/bash

# 🎯 MAESTROFIN - INICIAR DASHBOARD ANALYTICS
# Script para iniciar rapidamente o dashboard

echo ""
echo "🎼 =========================================="
echo "    MAESTROFIN - INICIANDO DASHBOARD"
echo "=========================================="
echo ""

# Verificar se o ambiente virtual existe
if [ ! -d ".venv" ]; then
    echo "❌ Ambiente virtual não encontrado!"
    echo "💡 Execute primeiro: python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

echo "🚀 Iniciando Dashboard Analytics..."
echo "📊 URL: http://localhost:5000"
echo "🔧 APIs: http://localhost:5000/health"
echo ""
echo "💡 Pressione Ctrl+C para parar"
echo ""

# Ativar ambiente virtual e iniciar dashboard
.venv/bin/python analytics/dashboard_app.py
