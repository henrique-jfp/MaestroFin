#!/usr/bin/env python3
"""
Teste rápido do sistema de analytics
"""

import sys
import os

# Adicionar o diretório atual ao Python path
sys.path.insert(0, os.getcwd())

try:
    from analytics.bot_analytics import analytics
    print("✅ Módulo analytics importado com sucesso!")
    
    # Testar inicialização do banco
    analytics.init_database()
    print("✅ Banco de dados inicializado!")
    
    # Testar algumas funções básicas
    from analytics.dashboard_app import app
    print("✅ Dashboard Flask carregado!")
    
    print("\n🚀 SISTEMA PRONTO PARA USO!")
    print("📊 Para iniciar: python start_complete_system.py")
    
except Exception as e:
    print(f"❌ Erro: {e}")
    print("\n🔧 Precisa de correção...")
