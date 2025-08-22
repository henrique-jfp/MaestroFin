#!/usr/bin/env python3
"""
MaestroFin - Launcher Simplificado
Inicia bot + dashboard de analytics
"""

import subprocess
import sys
import os
import time
import signal
from threading import Thread

def run_bot():
    """Executa o bot principal"""
    try:
        print("🤖 Iniciando MaestroFin Bot...")
        subprocess.run([sys.executable, "bot_production.py"], 
                      env=dict(os.environ, PYTHONPATH=os.getcwd()))
    except KeyboardInterrupt:
        print("\n🤖 Bot interrompido")

def run_dashboard():
    """Executa o dashboard de analytics"""
    try:
        print("📊 Iniciando Analytics Dashboard...")
        subprocess.run([sys.executable, "analytics/dashboard_app.py"], 
                      env=dict(os.environ, PYTHONPATH=os.getcwd()))
    except KeyboardInterrupt:
        print("\n📊 Dashboard interrompido")

def main():
    """Função principal"""
    print("=" * 50)
    print("🚀 MAESTROFIN - SISTEMA COMPLETO")
    print("=" * 50)
    print("Iniciando Bot Telegram + Analytics Dashboard...")
    print()
    
    try:
        # Criar threads para bot e dashboard
        bot_thread = Thread(target=run_bot, daemon=True)
        dashboard_thread = Thread(target=run_dashboard, daemon=True)
        
        # Iniciar serviços
        bot_thread.start()
        time.sleep(2)  # Aguardar bot iniciar
        dashboard_thread.start()
        
        print("\n✅ SERVIÇOS ATIVOS:")
        print("🤖 Bot Telegram: Rodando")
        print("📊 Analytics: http://localhost:5000")
        print("\n💡 Pressione Ctrl+C para parar tudo")
        
        # Manter programa rodando
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n⏹️  Parando todos os serviços...")
        print("✅ Sistema encerrado!")

if __name__ == "__main__":
    main()
