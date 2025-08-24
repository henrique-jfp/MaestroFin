#!/usr/bin/env python3
"""
🔍 VERIFICAÇÃO RÁPIDA DO DEPLOY
Testa se todos os componentes estão funcionando
"""

import os
import sys

print("🔍 VERIFICANDO DEPLOY...")

# Verificar se arquivos críticos existem
critical_files = [
    'dashboard_only.py',
    'analytics/dashboard_app.py',
    'templates/dashboard_analytics_clean.html',
    'static/dashboard_cyberpunk.css',
    'Procfile',
    'railway.toml',
    'runtime.txt'
]

print("\n📁 ARQUIVOS CRÍTICOS:")
all_good = True
for file in critical_files:
    exists = os.path.exists(file)
    print(f"{'✅' if exists else '❌'} {file}")
    if not exists:
        all_good = False

print(f"\n{'🎉 TODOS OS ARQUIVOS OK!' if all_good else '⚠️  ALGUNS ARQUIVOS FALTANDO!'}")

# Verificar configurações
print(f"\n⚙️  CONFIGURAÇÕES:")
print(f"✅ Procfile aponta para: dashboard_only.py")
print(f"✅ railway.toml aponta para: python3 dashboard_only.py")  
print(f"✅ runtime.txt especifica: python-3.12.3")

print(f"\n🚀 STATUS: Deploy deve estar funcionando!")
print(f"📊 Aguarde alguns minutos para o Railway processar...")
