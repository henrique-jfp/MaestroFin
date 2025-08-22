#!/usr/bin/env python3
"""
Launcher para MaestroFin Bot + Analytics Dashboard
Inicia o bot e o dashboard de analytics simultaneamente
"""

import subprocess
import threading
import time
import os
import sys
from pathlib import Path

def start_bot():
    """Inicia o bot principal"""
    print("🤖 Iniciando MaestroFin Bot...")
    subprocess.run([sys.executable, "bot_production.py"])

def start_analytics_dashboard():
    """Inicia o dashboard de analytics"""
    print("📊 Iniciando Analytics Dashboard...")
    # Definir PYTHONPATH para encontrar o módulo analytics
    env = os.environ.copy()
    env['PYTHONPATH'] = os.getcwd()
    subprocess.run([sys.executable, "analytics/dashboard_app.py"], env=env)

def main():
    """Função principal para iniciar tudo"""
    print("🚀 MAESTROFIN - SISTEMA COMPLETO")
    print("=" * 50)
    print("Iniciando Bot + Analytics Dashboard...")
    print("")
    
    # Thread para o bot
    bot_thread = threading.Thread(target=start_bot, daemon=True)
    bot_thread.start()
    
    # Aguardar um pouco para o bot inicializar
    time.sleep(3)
    
    # Thread para o dashboard
    dashboard_thread = threading.Thread(target=start_analytics_dashboard, daemon=True)
    dashboard_thread.start()
    
    print("")
    print("✅ Serviços iniciados:")
    print("  🤖 Bot Telegram: Ativo")
    print("  📊 Analytics: http://localhost:5000")
    print("")
    print("Pressione Ctrl+C para parar todos os serviços")
    
    try:
        # Manter o programa rodando
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n⏹️ Parando todos os serviços...")
        sys.exit(0)

if __name__ == "__main__":
    main()
