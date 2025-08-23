#!/usr/bin/env python3
"""
🚀 MAESTROFIN LAUNCHER - Inicializador Simples
Launcher alternativo para inicialização rápida dos componentes
"""

import subprocess
import sys
import time
import os
from pathlib import Path

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
        print("💡 Execute: pip install -r requirements.txt")
        return False

def start_bot_only():
    """Inicia apenas o bot do Telegram"""
    print("🤖 Iniciando apenas o Bot do Telegram...")
    try:
        subprocess.run([sys.executable, "bot.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro ao iniciar bot: {e}")
    except KeyboardInterrupt:
        print("🛑 Bot interrompido")

def start_dashboard_only():
    """Inicia apenas o dashboard"""
    print("🎨 Iniciando apenas o Dashboard...")
    try:
        from analytics.dashboard_app import app
        app.run(host='0.0.0.0', port=5001, debug=True)
    except ImportError:
        print("❌ Dashboard não encontrado em analytics/dashboard_app.py")
    except KeyboardInterrupt:
        print("🛑 Dashboard interrompido")

def start_complete_system():
    """Inicia o sistema completo"""
    print("🚀 Iniciando Sistema Completo...")
    try:
        subprocess.run([sys.executable, "start_system.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro ao iniciar sistema: {e}")
    except KeyboardInterrupt:
        print("🛑 Sistema interrompido")

def main():
    """Menu principal do launcher"""
    print("""
╭────────────────────────────────────╮
│     🎼 MAESTROFIN LAUNCHER 🎼      │
╰────────────────────────────────────╯

Escolha uma opção:
1. 🤖 Bot apenas (recomendado para produção)
2. 🎨 Dashboard apenas (desenvolvimento/análise)  
3. 🚀 Sistema completo (bot + dashboard + analytics)
4. ❌ Sair

""")
    
    # Verificar se estamos no diretório correto
    if not os.path.exists('bot.py'):
        print("❌ bot.py não encontrado!")
        print("💡 Certifique-se de estar no diretório do MaestroFin")
        return
    
    # Verificar dependências
    if not check_requirements():
        return
    
    while True:
        try:
            choice = input("Digite sua escolha (1-4): ").strip()
            
            if choice == '1':
                start_bot_only()
                break
            elif choice == '2':
                start_dashboard_only()
                break
            elif choice == '3':
                start_complete_system()
                break
            elif choice == '4':
                print("👋 Até logo!")
                break
            else:
                print("❌ Opção inválida. Digite 1, 2, 3 ou 4.")
                
        except KeyboardInterrupt:
            print("\n👋 Até logo!")
            break
        except Exception as e:
            print(f"❌ Erro: {e}")

if __name__ == "__main__":
    main()
