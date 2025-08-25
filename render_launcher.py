#!/usr/bin/env python3
"""
🚀 MAESTROFIN RENDER LAUNCHER
Launcher principal para deploy no Render.
Este arquivo detecta automaticamente se deve iniciar o bot ou o dashboard.
"""

import os
import sys
import subprocess
import logging

print("\n" + "="*70)
print("╭────────────────────────────────────────────────────────────────╮")
print("│              🎼 MAESTROFIN - RENDER LAUNCHER 🎼                │")
print("│                    🚀 Starting Application                     │")
print("╰────────────────────────────────────────────────────────────────╯")
print("="*70)

def main():
    """Função principal do launcher"""
    
    # Verificar variáveis de ambiente do Render
    render_service_type = os.getenv('RENDER_SERVICE_TYPE', '').lower()
    render_service_name = os.getenv('RENDER_SERVICE_NAME', '')
    port = os.getenv('PORT')
    
    print(f"🔍 RENDER_SERVICE_TYPE: {render_service_type}")
    print(f"🔍 RENDER_SERVICE_NAME: {render_service_name}")
    print(f"🔍 PORT: {port}")
    print(f"🔍 DATABASE_URL: {'Configurado' if os.getenv('DATABASE_URL') else 'Não configurado'}")
    
    # Lógica de decisão melhorada
    start_dashboard = False
    start_bot = False
    
    # Se tem PORT, provavelmente é web service
    if port:
        start_dashboard = True
        print("🌐 Detectado PORT - assumindo WEB SERVICE")
    
    # Se é explicitamente um worker, força bot
    if render_service_type == 'worker' or 'bot' in render_service_name.lower():
        start_dashboard = False
        start_bot = True
        print("🤖 Service name/type indica WORKER SERVICE")
    
    # Se é explicitamente web, força dashboard  
    if render_service_type == 'web' or 'dashboard' in render_service_name.lower():
        start_dashboard = True
        start_bot = False
        print("🌐 Service name/type indica WEB SERVICE")
    
    # Fallback - se nada foi detectado, inicia ambos (para deploy simples)
    if not start_dashboard and not start_bot:
        print("⚠️ Não foi possível detectar o tipo de serviço")
        if port:
            start_dashboard = True
            print("� Fallback: iniciando DASHBOARD (PORT disponível)")
        else:
            start_bot = True  
            print("📍 Fallback: iniciando BOT (sem PORT)")
    
    # Executar o serviço apropriado
    if start_dashboard:
        print("🌐 INICIANDO DASHBOARD")
        print("🎯 Comando: gunicorn --config gunicorn_config.py web_launcher:app")
        print("-" * 50)
        
        try:
            subprocess.run(['gunicorn', '--config', 'gunicorn_config.py', 'web_launcher:app'], check=True)
        except subprocess.CalledProcessError as e:
            print(f"❌ Erro ao iniciar Gunicorn: {e}")
            # Fallback para Flask direto
            print("🔄 Tentando Flask direto...")
            port_value = os.environ.get("PORT", "10000")
            subprocess.run(['python', '-c', f'import os; from analytics.dashboard_app_render_fixed import app; app.run(host="0.0.0.0", port={port_value})'])
        
    elif start_bot:
        print("🤖 INICIANDO BOT TELEGRAM")
        print("🎯 Comando: python bot.py")
        print("-" * 50)
        
        subprocess.run(['python', 'bot.py'], check=True)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Aplicação interrompida pelo usuário")
        sys.exit(0)
    except Exception as e:
        print(f"❌ ERRO CRÍTICO: {e}")
        logging.error(f"Render Launcher Error: {e}")
        sys.exit(1)
