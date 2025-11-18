#!/usr/bin/env python3
"""
🚀 MAESTRO FINANCEIRO - Launcher Principal para Render
Launcher unificado e otimizado para produção
"""

import os
import sys
import logging
import asyncio
from threading import Thread
import signal

# Configurar logging básico
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_environment():
    """Carrega variáveis de ambiente"""
    try:
        # Tentar carregar .env se existir localmente
        if os.path.exists('.env'):
            from dotenv import load_dotenv
            load_dotenv()
            logger.info("✅ Arquivo .env carregado")
        
        # Verificar variáveis essenciais
        required_vars = [
            'TELEGRAM_TOKEN',
            'DATABASE_URL'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            logger.error(f"❌ Variáveis de ambiente faltando: {missing_vars}")
            return False
        
        logger.info("✅ Todas as variáveis essenciais estão configuradas")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao carregar ambiente: {e}")
        return False

def start_health_check_server():
    """Inicia servidor HTTP simples para health checks (Koyeb/Render)"""
    from flask import Flask
    
    health_app = Flask(__name__)
    
    @health_app.route('/')
    @health_app.route('/health')
    @health_app.route('/healthz')
    def health():
        return {'status': 'healthy', 'service': 'maestrofin-bot'}, 200
    
    port = int(os.getenv('PORT', 8000))
    logger.info(f"🏥 Health check server iniciado na porta {port}")
    
    # Rodar em modo silencioso
    import logging as flask_logging
    flask_log = flask_logging.getLogger('werkzeug')
    flask_log.setLevel(flask_logging.ERROR)
    
    health_app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

def start_telegram_bot():
    """Inicia o bot do Telegram"""
    try:
        logger.info("🤖 Iniciando bot do Telegram...")
        logger.info(f"📍 Python version: {sys.version}")
        logger.info(f"📍 Working directory: {os.getcwd()}")
        logger.info(f"📍 TELEGRAM_TOKEN presente: {bool(os.getenv('TELEGRAM_TOKEN'))}")
        
        # 🏥 INICIAR HEALTH CHECK SERVER EM THREAD SEPARADA
        # (Para Koyeb/Render que precisam de health checks HTTP)
        if os.getenv('PORT'):
            health_thread = Thread(target=start_health_check_server, daemon=True)
            health_thread.start()
            logger.info("✅ Health check server iniciado em thread separada")
        
        try:
            logger.info("📦 Importando módulo bot...")
            from bot import create_application
            logger.info("✅ Módulo bot importado com sucesso!")
            
            logger.info("🔧 Criando aplicação do bot...")
            application = create_application()
            logger.info("✅ Aplicação criada!")
            
            if application:
                logger.info("🚀 Iniciando polling do bot (isso pode demorar 10-30s)...")
                application.run_polling(allowed_updates=None, drop_pending_updates=True)
                logger.info("✅ Bot iniciado com sucesso!")
            else:
                logger.error("❌ Falha ao criar aplicação do bot")
                sys.exit(1)
                
        except Exception as e:
            logger.error(f"❌ ERRO FATAL ao importar/iniciar bot: {e}", exc_info=True)
            import traceback
            logger.error(f"📋 Traceback completo:\n{traceback.format_exc()}")
            sys.exit(1)
        
    except Exception as e:
        logger.error(f"❌ Erro no bot do Telegram: {e}", exc_info=True)
        sys.exit(1)

def start_dashboard():
    """Inicia o dashboard Flask"""
    try:
        logger.info("📊 Iniciando dashboard Flask...")
        from analytics.dashboard_app import app
        
        port = int(os.getenv('PORT', 10000))
        app.run(
            host='0.0.0.0',
            port=port,
            debug=False,
            use_reloader=False
        )
        
    except Exception as e:
        logger.error(f"❌ Erro no dashboard: {e}")
        sys.exit(1)

def signal_handler(signum, frame):
    """Handler para sinais de sistema"""
    logger.info("🛑 Sinal de parada recebido. Encerrando...")
    sys.exit(0)

def apply_migrations():
    """Aplica migrations pendentes no banco de dados"""
    try:
        logger.info("🔄 Verificando migrations pendentes...")
        
        # Importar após carregar ambiente
        from pathlib import Path
        import psycopg2
        
        DATABASE_URL = os.getenv("DATABASE_URL")
        migration_file = Path(__file__).parent / "migrations" / "002_create_pluggy_tables.sql"
        
        if not migration_file.exists():
            logger.warning(f"⚠️  Migration não encontrada: {migration_file}")
            return
        
        # Conectar e aplicar
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Verificar se tabelas já existem
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_name = 'pluggy_items'
        """)
        
        if cursor.fetchone()[0] > 0:
            logger.info("ℹ️  Tabelas Open Finance já existem, pulando migration")
            cursor.close()
            conn.close()
            return
        
        # Aplicar migration
        logger.info("📄 Aplicando migration 002: Tabelas Open Finance/Pluggy")
        with open(migration_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        cursor.execute(sql_content)
        conn.commit()
        
        logger.info("✅ Migration 002 aplicada com sucesso!")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        logger.error(f"❌ Erro ao aplicar migrations: {e}")
        # Não falhar a aplicação por causa de migration
        # As tabelas podem já existir ou ser criadas depois

def main():
    """Função principal"""
    logger.info("🚀 Iniciando Maestro Financeiro...")
    
    # Configurar handler de sinais
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Carregar ambiente
    if not load_environment():
        logger.error("❌ Falha ao carregar ambiente. Encerrando...")
        sys.exit(1)
    
    # Aplicar migrations
    apply_migrations()
    
    # Verificar modo de execução
    # Priorizar variável manual MAESTROFIN_MODE
    force_mode = os.getenv('MAESTROFIN_MODE', '').lower()
    port = os.getenv('PORT')
    is_render = os.getenv('RENDER') or os.getenv('RAILWAY_ENVIRONMENT')
    
    logger.info(f"🔍 Detecção de modo:")
    logger.info(f"  MAESTROFIN_MODE={force_mode}")
    logger.info(f"  PORT={port}")
    logger.info(f"  RENDER={os.getenv('RENDER')}")
    logger.info(f"  RAILWAY_ENVIRONMENT={os.getenv('RAILWAY_ENVIRONMENT')}")
    logger.info(f"  is_render={is_render}")
    
    # Se MAESTROFIN_MODE está setado, usar ele
    if force_mode == 'bot':
        logger.info("🤖 Modo FORÇADO: BOT (via MAESTROFIN_MODE=bot)")
        start_telegram_bot()
        
    elif force_mode == 'dashboard':
        logger.info("🌐 Modo FORÇADO: DASHBOARD (via MAESTROFIN_MODE=dashboard)")
        start_dashboard()
        
    elif port and is_render:
        # Modo web - rodar dashboard Flask (Render Web Service)
        logger.info("🌐 Modo WEB (Render): Iniciando dashboard Flask")
        start_dashboard()
        
    elif is_render and not port:
        # Modo worker - rodar bot Telegram (Render Worker)
        logger.info("🤖 Modo WORKER (Render): Iniciando bot Telegram")
        start_telegram_bot()
        
    else:
        # Modo local - rodar ambos em threads separadas
        logger.info("🔄 Modo LOCAL: Iniciando bot e dashboard")
        
        # Thread para o bot
        bot_thread = Thread(target=start_telegram_bot, daemon=True)
        bot_thread.start()
        
        # Dashboard na thread principal
        start_dashboard()

if __name__ == "__main__":
    main()
