#!/usr/bin/env python3
"""
🤖 BOT LAUNCHER DIRETO
Inicia APENAS o bot do Telegram, sem detecção.
Use este arquivo como startCommand para o Worker Service.
"""

import os
import sys

print("\n" + "="*60)
print("╭──────────────────────────────────────────────────────╮")
print("│              🤖 MAESTROFIN BOT LAUNCHER              │")
print("│                 🚀 Worker Service                    │")
print("╰──────────────────────────────────────────────────────╯")
print("="*60)

def main():
    """Launcher direto do bot"""
    try:
        print("🔧 Configurando ambiente...")
        
        # Configurar environment
        os.environ['MAESTROFIN_BOT_MODE'] = 'true'
        
        print("🤖 Iniciando Bot do Telegram...")
        print("📍 Executando: python bot.py")
        
        # Importar e executar bot diretamente
        import bot  # Isso executará o bot.py
        
    except KeyboardInterrupt:
        print("\n🛑 Bot interrompido pelo usuário")
    except Exception as e:
        print(f"❌ Erro crítico no bot: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
