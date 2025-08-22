#!/bin/bash
# Railway Build Script
echo "🔧 RAILWAY BUILD - Forçando Flask 3.1.0"

# Atualizar pip primeiro
pip install --upgrade pip

# Forçar reinstalação do Flask na versão correta
pip uninstall flask -y
pip install Flask==3.1.0

# Instalar o resto dos requirements
pip install -r requirements.txt
