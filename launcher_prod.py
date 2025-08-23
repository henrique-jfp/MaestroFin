#!/usr/bin/env python3
"""
🚀 MAESTROFIN PRODUCTION LAUNCHER
Launcher otimizado para Railway/produção
"""

import subprocess
import sys
import time
import os
from pathlib import Path
import threading

def check_requirements():
    """Verifica se os requisitos estão instalados"""
    try:
        import telegram
        import flask
        import sqlalchemy
        import pandas
        print("✅ Dependências básicas encontradas")
        return True
    except ImportError as e:
        print(f"❌ Dependência faltando: {e}")
        return False

def start_bot():
    """Inicia o bot do Telegram como thread"""
    print("🤖 Iniciando Bot do Telegram...")
    try:
        subprocess.run([sys.executable, "bot.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro ao iniciar bot: {e}")
        return False
    return True

def start_dashboard():
    """Inicia o dashboard analytics no processo principal"""
    print("📊 Iniciando Dashboard Analytics...")
    try:
        from analytics.dashboard_app import app
        # Railway usa a variável PORT, precisamos usar ela no processo principal
        port = int(os.getenv('PORT', 8080))
        print(f"📊 Dashboard rodando na porta {port}")
        app.run(host='0.0.0.0', port=port, debug=False)
    except Exception as e:
        print(f"❌ Erro ao iniciar dashboard: {e}")
        sys.exit(1)

def main():
    """Função principal para produção"""
    print("\n" + "="*50)
    print("╭──────────────────────────────────────────────╮")
    print("│        🎼 MAESTROFIN PRODUCTION 🎼           │")
    print("│              Railway Deploy                  │")
    print("╰──────────────────────────────────────────────╯")
    print("="*50)
    
    # Verificar dependências
    if not check_requirements():
        print("❌ Dependências não encontradas")
        sys.exit(1)
    
    # Verificar se bot.py existe
    if not os.path.exists('bot.py'):
        print("❌ bot.py não encontrado!")
        sys.exit(1)
    
    # Importar config para carregar variáveis
    try:
        import config
        print("✅ Configurações carregadas")
    except Exception as e:
        print(f"❌ Erro ao carregar config: {e}")
        sys.exit(1)
    
    # Verificar variáveis essenciais
    telegram_token = os.getenv('TELEGRAM_TOKEN')
    if not telegram_token:
        print("❌ TELEGRAM_TOKEN não configurado!")
        print("Configure com: railway variables --set 'TELEGRAM_TOKEN=seu_token'")
        sys.exit(1)
    
    print("✅ Token do Telegram configurado")
    print("🚀 Iniciando sistema completo...")
    
    # Iniciar bot em thread separada 
    bot_thread = threading.Thread(target=start_bot, daemon=True)
    bot_thread.start()
    
    # Aguardar um pouco para bot inicializar
    time.sleep(5)
    print("🤖 Bot iniciado em background")
    
    # Iniciar dashboard no processo principal (Railway precisa disso)
    start_dashboard()

if __name__ == "__main__":
    main()
