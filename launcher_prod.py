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
    """Inicia o bot do Telegram"""
    print("🤖 Iniciando Bot do Telegram...")
    try:
        subprocess.run([sys.executable, "bot.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro ao iniciar bot: {e}")
        sys.exit(1)

def start_dashboard():
    """Inicia o dashboard analytics"""
    print("📊 Iniciando Dashboard Analytics...")
    try:
        from analytics.dashboard_app import app
        port = int(os.getenv('PORT', 5001))
        app.run(host='0.0.0.0', port=port, debug=False)
    except Exception as e:
        print(f"❌ Erro ao iniciar dashboard: {e}")

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
    
    # Verificar variáveis essenciais
    telegram_token = os.getenv('TELEGRAM_TOKEN')
    if not telegram_token:
        print("❌ TELEGRAM_TOKEN não configurado!")
        print("Configure com: railway variables --set 'TELEGRAM_TOKEN=seu_token'")
        sys.exit(1)
    
    print("✅ Token do Telegram configurado")
    print("🚀 Iniciando sistema completo...")
    
    # Iniciar dashboard em thread separada
    dashboard_thread = threading.Thread(target=start_dashboard, daemon=True)
    dashboard_thread.start()
    
    # Aguardar um pouco para dashboard inicializar
    time.sleep(3)
    print("📊 Dashboard iniciado na porta 5001")
    
    # Iniciar bot (processo principal)
    start_bot()

if __name__ == "__main__":
    main()
