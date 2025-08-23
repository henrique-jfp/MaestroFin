#!/usr/bin/env python3
"""
🚀 SIMPLE LAUNCHER FOR RAILWAY
Launcher ultra-simples para debug
"""

import os
import sys
import subprocess

def main():
    print("🚀 MAESTROFIN SIMPLE LAUNCHER")
    print(f"Python: {sys.version}")
    print(f"Working dir: {os.getcwd()}")
    
    # Verificar variáveis principais
    token = os.getenv('TELEGRAM_TOKEN')
    port = os.getenv('PORT', '8080')
    
    print(f"TELEGRAM_TOKEN: {'✅ Configurado' if token else '❌ Não encontrado'}")
    print(f"PORT: {port}")
    
    if not token:
        print("❌ Sem token, saindo...")
        sys.exit(1)
    
    # Importar config para inicializar variáveis
    try:
        print("📋 Carregando configurações...")
        import config
        print("✅ Config carregado")
    except Exception as e:
        print(f"❌ Erro no config: {e}")
        sys.exit(1)
    
    # Tentar iniciar o bot diretamente
    print("🤖 Iniciando bot...")
    try:
        subprocess.run([sys.executable, "bot.py"], check=True)
    except Exception as e:
        print(f"❌ Erro ao iniciar bot: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
