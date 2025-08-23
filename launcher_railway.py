#!/usr/bin/env python3
"""
🚀 MAESTROFIN SIMPLE LAUNCHER for RAILWAY
Launcher simplificado especificamente para Railway
"""

import os
import sys
import time
import threading
import subprocess
import signal

print("\n" + "="*50)
print("╭──────────────────────────────────────────────╮")
print("│        🎼 MAESTROFIN PRODUCTION 🎼           │")
print("│              Railway Deploy                  │")
print("╰──────────────────────────────────────────────╯")
print("="*50)

# Verificar dependências básicas
try:
    import telegram
    import flask
    print("✅ Dependências básicas encontradas")
except ImportError as e:
    print(f"❌ Dependência faltando: {e}")
    sys.exit(1)

# Carregar configurações
try:
    import config
    print("INFO:root:🌐 [PROD] Ambiente de produção detectado - usando variáveis de ambiente do sistema")
    print("INFO:root:✅ Configurações carregadas:")
    print(f"INFO:root:   📱 TELEGRAM_TOKEN: {'✅ Configurado' if os.getenv('TELEGRAM_TOKEN') else '❌ Não configurado'}")
    print(f"INFO:root:   🤖 GEMINI_API_KEY: {'✅ Configurado' if os.getenv('GEMINI_API_KEY') else '❌ Não configurado'}")
    print(f"INFO:root:   🗄️ DATABASE_URL: {'✅ Configurado' if os.getenv('DATABASE_URL') else '❌ Não configurado'}")
    if not os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
        print("INFO:root:ℹ️ GOOGLE_APPLICATION_CREDENTIALS não configurado - funcionalidades OCR limitadas")
    print("✅ Configurações carregadas")
except Exception as e:
    print(f"❌ Erro ao carregar config: {e}")
    sys.exit(1)

# Verificar token obrigatório
if not os.getenv('TELEGRAM_TOKEN'):
    print("❌ TELEGRAM_TOKEN não configurado!")
    sys.exit(1)

print("✅ Token do Telegram configurado")
print("🚀 Iniciando sistema completo...")

def start_dashboard():
    """Inicia dashboard em thread separada"""
    try:
        print("📊 Iniciando Dashboard Analytics...")
        from analytics.dashboard_app import app
        port = int(os.getenv('PORT', 8080))
        print(f"📊 Dashboard rodando na porta {port}")
        app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
    except Exception as e:
        print(f"❌ Erro no dashboard: {e}")

def start_bot():
    """Inicia bot em processo separado"""
    try:
        print("🤖 Iniciando Bot do Telegram...")
        
        # Importar e executar a função main do bot
        from bot import main
        main()  # Chama diretamente a função main
        
    except Exception as e:
        print(f"❌ Erro ao iniciar bot: {e}")
        return False
    return True

# Iniciar dashboard em thread separada
dashboard_thread = threading.Thread(target=start_dashboard, daemon=True)
dashboard_thread.start()
print("📊 Dashboard iniciado na porta especificada")

# Iniciar bot no processo principal
start_bot()
