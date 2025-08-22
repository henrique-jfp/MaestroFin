#!/usr/bin/env python3
"""
MaestroFin Bot - Production ready version with health check
"""

import logging
import warnings
import google.generativeai as genai
import os
import threading
from datetime import time
from telegram.warnings import PTBUserWarning
from flask import Flask, jsonify

# Suprimir warnings específicos do python-telegram-bot
warnings.filterwarnings("ignore", category=PTBUserWarning, module="telegram")

# Servidor web para health check (Railway/Azure requer isso)
health_app = Flask(__name__)

@health_app.route('/health')
def health_check():
    """Endpoint de health check para Railway/Azure"""
    return jsonify({
        "status": "healthy", 
        "service": "MaestroFin Bot",
        "version": "3.1.0"
    })

@health_app.route('/')
def home():
    """Endpoint raiz com informações do serviço"""
    return jsonify({
        "service": "MaestroFin - Bot Financeiro",
        "status": "running",
        "version": "3.1.0",
        "description": "Bot Telegram para gestão financeira com IA",
        "features": [
            "Análise de faturas com OCR",
            "Gráficos dinâmicos",
            "IA conversacional",
            "Sistema de gamificação",
            "Relatórios inteligentes"
        ]
    })

def run_health_server():
    """Executa o servidor Flask em thread separada"""
    port = int(os.environ.get('PORT', 8080))
    health_app.run(host='0.0.0.0', port=port, debug=False)

def start_health_server():
    """Inicia o servidor de health check em background"""
    health_thread = threading.Thread(target=run_health_server)
    health_thread.daemon = True
    health_thread.start()
    logging.info(f"🌐 Health check server iniciado na porta {os.environ.get('PORT', 8080)}")

# Importar o bot original
from bot import main as original_main

def main():
    """Função principal com health check integrado"""
    # Configurar logging
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    logger = logging.getLogger(__name__)
    
    logger.info("🚀 Iniciando MaestroFin Bot v3.1.0 - Production Mode")
    
    # Iniciar servidor de health check
    start_health_server()
    
    # Executar bot principal
    try:
        original_main()
    except KeyboardInterrupt:
        logger.info("⏹️ Bot encerrado pelo usuário")
    except Exception as e:
        logger.error(f"❌ Erro crítico no bot: {e}")
        raise

if __name__ == '__main__':
    main()
