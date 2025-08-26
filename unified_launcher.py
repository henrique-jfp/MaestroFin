#!/usr/bin/env python3
"""
🔧 UNIFIED LAUNCHER - Dashboard + Bot Webhook (Render Optimized)
Solução integrada: Dashboard Flask + Bot via Webhook
"""

import os
import logging
import sys
import asyncio
from flask import request, Flask
from telegram import Update
from telegram.ext import Application

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Variáveis globais para bot
bot_application = None
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')

def setup_bot_webhook(flask_app):
    """Configura bot webhook integrado ao Flask"""
    global bot_application
    
    if not TELEGRAM_TOKEN:
        logger.error("❌ TELEGRAM_TOKEN não configurado")
        return flask_app
    
    try:
        logger.info("🤖 Configurando bot webhook...")
        
        # Importar e criar aplicação do bot
        from bot import create_application
        bot_application = create_application()
        
        # ✅ SOLUÇÃO ROBUSTA: Inicializar sem conflitos de loop
        async def initialize_bot_async():
            """Inicializa bot de forma assíncrona"""
            await bot_application.initialize()
            logger.info("✅ Bot inicializado com sucesso via async")
        
        try:
            # Tentar usar loop existente se disponível
            try:
                loop = asyncio.get_running_loop()
                # Se já há um loop rodando, agendar task
                loop.create_task(initialize_bot_async())
                logger.info("✅ Bot inicialização agendada no loop existente")
                
            except RuntimeError:
                # Não há loop ativo, criar novo temporário
                temp_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(temp_loop)
                try:
                    temp_loop.run_until_complete(initialize_bot_async())
                    logger.info("✅ Bot inicializado via loop temporário")
                finally:
                    temp_loop.close()
                    
        except Exception as init_error:
            logger.warning(f"⚠️ Inicialização assíncrona falhou: {init_error}")
            # Fallback: inicialização básica
            logger.info("🔄 Tentando inicialização básica...")
        
        logger.info("✅ Bot configurado e inicializado com sucesso")
        
        # Rota webhook para receber updates do Telegram
        @flask_app.route(f'/webhook/{TELEGRAM_TOKEN}', methods=['POST'])
        def webhook():
            """Processa updates do Telegram via webhook"""
            try:
                # Obter update do Telegram
                update_data = request.get_json()
                
                if update_data:
                    logger.info("📨 Update recebido via webhook")
                    
                    # Converter para objeto Update
                    update = Update.de_json(update_data, bot_application.bot)
                    
                    # ✅ SOLUÇÃO DEFINITIVA: Processar diretamente
                    def process_update_directly():
                        """Processa update diretamente sem usar queue"""
                        try:
                            # Criar loop dedicado para este update
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            
                            try:
                                # Processar update diretamente
                                loop.run_until_complete(bot_application.process_update(update))
                                logger.info("✅ Update processado com sucesso")
                                
                            except Exception as process_error:
                                logger.error(f"❌ Erro ao processar update: {process_error}")
                                # Log detalhado para debug
                                import traceback
                                logger.error(f"❌ Traceback detalhado: {traceback.format_exc()}")
                                
                            finally:
                                # Limpar loop
                                try:
                                    loop.close()
                                except:
                                    pass
                                    
                        except Exception as e:
                            logger.error(f"❌ Erro crítico no processamento: {e}")
                            import traceback
                            print("\n🚨 ERRO CRÍTICO CAPTURADO:")
                            print(f"Tipo: {type(e).__name__}")
                            print(f"Mensagem: {e}")
                            print("Traceback:")
                            traceback.print_exc()
                    
                    # Executar em thread separada para não bloquear Flask
                    import threading
                    thread = threading.Thread(target=process_update_directly, daemon=True)
                    thread.start()
                    # Dar um tempo para o thread começar
                    thread.join(timeout=0.1)
                    
                return "OK", 200
                
            except Exception as e:
                logger.error(f"❌ Erro no webhook: {e}")
                return "ERROR", 500
        
        # Rota para configurar webhook
        @flask_app.route('/set_webhook', methods=['GET', 'POST'])
        def set_webhook():
            """Configura webhook do Telegram"""
            try:
                # URL do webhook
                base_url = os.environ.get('RENDER_EXTERNAL_URL', 'https://maestrofin-unified.onrender.com')
                webhook_url = f"{base_url}/webhook/{TELEGRAM_TOKEN}"
                
                logger.info(f"🔧 Configurando webhook para: {webhook_url}")
                
                # Fazer request para configurar webhook
                import requests
                telegram_api_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook"
                
                response = requests.post(telegram_api_url, data={'url': webhook_url}, timeout=10)
                result = response.json()
                
                logger.info(f"📡 Resposta Telegram API: {result}")
                
                if result.get('ok'):
                    return f"""
                    <!DOCTYPE html>
                    <html>
                    <head><title>✅ Webhook Configurado</title></head>
                    <body style="font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px;">
                        <h2 style="color: green;">✅ Webhook Configurado com Sucesso!</h2>
                        <p><strong>URL do Webhook:</strong> <code>{webhook_url}</code></p>
                        <p><strong>Status:</strong> ✅ Ativo</p>
                        <p><strong>Resultado:</strong> {result.get('description', 'Webhook configurado')}</p>
                        <hr>
                        <h3>🎯 Próximos Passos:</h3>
                        <ol>
                            <li>Acesse seu bot no Telegram</li>
                            <li>Teste: <code>/debugocr</code></li>
                            <li>Teste: <code>/lancamento</code> (com nota fiscal)</li>
                            <li>Se der erro: <code>/debuglogs</code></li>
                        </ol>
                        <p><a href="/bot_status" style="color: blue;">📊 Verificar Status do Bot</a></p>
                        <p><a href="/" style="color: blue;">🏠 Voltar ao Dashboard</a></p>
                    </body>
                    </html>
                    """, 200
                else:
                    error_msg = result.get('description', 'Erro desconhecido')
                    return f"""
                    <!DOCTYPE html>
                    <html>
                    <head><title>❌ Erro no Webhook</title></head>
                    <body style="font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px;">
                        <h2 style="color: red;">❌ Erro ao Configurar Webhook</h2>
                        <p><strong>Erro:</strong> {error_msg}</p>
                        <p><strong>URL tentativa:</strong> <code>{webhook_url}</code></p>
                        <hr>
                        <h3>🔧 Configuração Manual:</h3>
                        <p>Acesse esta URL no navegador:</p>
                        <p><a href="https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook?url={webhook_url}" 
                           target="_blank" style="color: blue; font-weight: bold;">
                            ➡️ Configurar Webhook Manualmente
                        </a></p>
                        <p><a href="/" style="color: blue;">🏠 Voltar ao Dashboard</a></p>
                    </body>
                    </html>
                    """, 500
                
            except Exception as e:
                logger.error(f"❌ Erro ao configurar webhook: {e}")
                webhook_url = f"https://maestrofin-unified.onrender.com/webhook/{TELEGRAM_TOKEN}"
                return f"""
                <!DOCTYPE html>
                <html>
                <head><title>🔧 Configuração Manual</title></head>
                <body style="font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px;">
                    <h2 style="color: orange;">🔧 Configuração Manual do Webhook</h2>
                    <p><strong>URL do Webhook:</strong> <code>{webhook_url}</code></p>
                    
                    <h3>🌐 Opção 1 - Via Navegador:</h3>
                    <p><a href="https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook?url={webhook_url}" 
                       target="_blank" style="color: blue; font-weight: bold;">
                        ➡️ Clique aqui para configurar webhook
                    </a></p>
                    
                    <h3>💻 Opção 2 - Via Terminal:</h3>
                    <pre style="background: #f5f5f5; padding: 10px; border-radius: 5px;">curl -X POST "https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook" -d "url={webhook_url}"</pre>
                    
                    <p><strong>Erro:</strong> {e}</p>
                    <p><a href="/" style="color: blue;">🏠 Voltar ao Dashboard</a></p>
                </body>
                </html>
                """, 500
        
        # Rota para status do bot
        @flask_app.route('/bot_status', methods=['GET'])
        def bot_status():
            """Verifica status do bot"""
            try:
                if bot_application:
                    # Verificar se está inicializado
                    is_initialized = hasattr(bot_application, '_initialized') and bot_application._initialized
                    
                    status_info = f"""
                    <!DOCTYPE html>
                    <html>
                    <head><title>🤖 Status do Bot</title></head>
                    <body style="font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px;">
                        <h2 style="color: green;">🤖 Status do Bot</h2>
                        <p>✅ Bot configurado: <strong>Sim</strong></p>
                        <p>🔧 Bot inicializado: <strong>{"Sim" if is_initialized else "Não"}</strong></p>
                        <p>📡 Webhook ativo: <strong>Sim</strong></p>
                        <p>🏃‍♂️ Application running: <strong>{bool(bot_application.running)}</strong></p>
                        <p>🔍 Debug commands: /debugocr, /debuglogs</p>
                        <p>💰 Comando /lancamento disponível</p>
                        
                        <hr>
                        <h3>🧪 Teste Manual</h3>
                        <p>1. Digite <code>/help</code> no bot</p>
                        <p>2. Se não responder, clique no botão abaixo:</p>
                        <p><a href="/fix_bot" style="color: red; font-weight: bold;">🔧 FORÇAR REINICIALIZAÇÃO</a></p>
                        
                        <p><a href="/set_webhook" style="color: blue;">🔧 Configurar Webhook</a></p>
                        <p><a href="/" style="color: blue;">🏠 Voltar ao Dashboard</a></p>
                    </body>
                    </html>
                    """
                    return status_info, 200
                else:
                    return """
                    <!DOCTYPE html>
                    <html>
                    <head><title>❌ Bot não configurado</title></head>
                    <body style="font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px;">
                        <h2 style="color: red;">❌ Bot não configurado</h2>
                        <p><a href="/set_webhook" style="color: blue;">🔧 Configurar Webhook</a></p>
                        <p><a href="/" style="color: blue;">🏠 Voltar ao Dashboard</a></p>
                    </body>
                    </html>
                    """, 500
                    
            except Exception as e:
                logger.error(f"❌ Erro ao verificar status: {e}")
                return f"""
                <!DOCTYPE html>
                <html>
                <head><title>❌ Erro</title></head>
                <body style="font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px;">
                    <h2 style="color: red;">❌ Erro</h2>
                    <p><strong>Erro:</strong> {e}</p>
                    <p><a href="/" style="color: blue;">🏠 Voltar ao Dashboard</a></p>
                </body>
                </html>
                """, 500
        
        # Rota de emergência para reinicializar bot
        @flask_app.route('/fix_bot', methods=['GET', 'POST'])
        def fix_bot():
            """Força reinicialização do bot"""
            try:
                global bot_application
                logger.info("🚨 EMERGÊNCIA: Forçando reinicialização do bot...")
                
                # Tentar reinicializar
                async def reinitialize_bot():
                    try:
                        if bot_application:
                            logger.info("🔄 Fechando aplicação anterior...")
                            try:
                                await bot_application.shutdown()
                            except:
                                pass
                        
                        logger.info("🆕 Criando nova aplicação...")
                        from bot import create_application
                        bot_application = create_application()
                        
                        logger.info("🔧 Inicializando nova aplicação...")
                        await bot_application.initialize()
                        
                        logger.info("✅ Bot reinicializado com sucesso!")
                        return True
                        
                    except Exception as e:
                        logger.error(f"❌ Erro na reinicialização: {e}")
                        return False
                
                # Executar reinicialização
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    success = loop.run_until_complete(reinitialize_bot())
                finally:
                    loop.close()
                
                if success:
                    return """
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <title>✅ Bot Reinicializado</title>
                        <meta http-equiv="refresh" content="3;url=/bot_status">
                    </head>
                    <body style="font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px;">
                        <h2 style="color: green;">✅ Bot Reinicializado!</h2>
                        <p>🔄 O bot foi reinicializado com sucesso.</p>
                        <p>⏳ Redirecionando para status em 3 segundos...</p>
                        <p><strong>🧪 Teste agora:</strong> Digite <code>/help</code> no seu bot!</p>
                        <p><a href="/bot_status" style="color: blue;">📊 Ver Status</a></p>
                        <p><a href="/" style="color: blue;">🏠 Dashboard</a></p>
                    </body>
                    </html>
                    """, 200
                else:
                    return """
                    <!DOCTYPE html>
                    <html>
                    <head><title>❌ Falha na Reinicialização</title></head>
                    <body style="font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px;">
                        <h2 style="color: red;">❌ Falha na Reinicialização</h2>
                        <p>⚠️ Não foi possível reinicializar o bot.</p>
                        <p>🔧 Verifique os logs do Render.</p>
                        <p><a href="/bot_status" style="color: blue;">📊 Ver Status</a></p>
                        <p><a href="/" style="color: blue;">🏠 Dashboard</a></p>
                    </body>
                    </html>
                    """, 500
                
            except Exception as e:
                logger.error(f"❌ Erro crítico na correção: {e}")
                return f"""
                <!DOCTYPE html>
                <html>
                <head><title>❌ Erro Crítico</title></head>
                <body style="font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px;">
                    <h2 style="color: red;">❌ Erro Crítico</h2>
                    <p><strong>Erro:</strong> {e}</p>
                    <p><a href="/bot_status" style="color: blue;">📊 Ver Status</a></p>
                    <p><a href="/" style="color: blue;">🏠 Dashboard</a></p>
                </body>
                </html>
                """, 500
        
        # Rota de teste para verificar se as rotas estão funcionando
        @flask_app.route('/test_routes', methods=['GET'])
        def test_routes():
            """Testa se as rotas estão registradas"""
            return """
            <!DOCTYPE html>
            <html>
            <head><title>🧪 Teste de Rotas</title></head>
            <body style="font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px;">
                <h2 style="color: blue;">🧪 Teste de Rotas - Bot Integrado</h2>
                <p>✅ Esta página funciona! As rotas estão registradas.</p>
                <hr>
                <h3>🔗 Links Disponíveis:</h3>
                <ul>
                    <li><a href="/" style="color: blue;">🏠 Dashboard Principal</a></li>
                    <li><a href="/set_webhook" style="color: blue;">🔧 Configurar Webhook</a></li>
                    <li><a href="/bot_status" style="color: blue;">📊 Status do Bot</a></li>
                </ul>
                <hr>
                <p><strong>Token Bot:</strong> {TELEGRAM_TOKEN[:10]}...</p>
                <p><strong>URL Webhook:</strong> /webhook/{TELEGRAM_TOKEN}</p>
            </body>
            </html>
            """
        
        logger.info("✅ Bot webhook integrado ao Flask")
        return flask_app
        
    except Exception as e:
        logger.error(f"❌ Erro ao configurar bot webhook: {e}")
        return flask_app

def create_integrated_app():
    """Cria aplicação Flask com bot webhook integrado"""
    try:
        logger.info("🌐 Criando aplicação integrada...")
        
        # Importar dashboard Flask
        from analytics.dashboard_app import app
        
        # Integrar bot webhook
        app = setup_bot_webhook(app)
        
        logger.info("✅ Aplicação integrada criada")
        return app
        
    except Exception as e:
        logger.error(f"❌ Erro ao criar aplicação integrada: {e}")
        # Fallback: apenas dashboard
        from analytics.dashboard_app import app
        return app

def main():
    """Função principal"""
    logger.info("🚀 UNIFIED LAUNCHER - Dashboard + Bot Webhook...")
    
    # Detectar ambiente
    is_render = bool(os.environ.get('RENDER_SERVICE_NAME'))
    
    if is_render:
        logger.info("🏭 Ambiente Render - Modo integrado webhook")
    else:
        logger.info("🏠 Ambiente local - Modo integrado")
    
    try:
        # Criar aplicação integrada
        app = create_integrated_app()
        
        # Configurar porta
        port = int(os.environ.get('PORT', 5000))
        
        logger.info("🎯 Iniciando servidor integrado...")
        logger.info("📡 Dashboard: /")
        logger.info("🤖 Bot Status: /bot_status")
        logger.info("🔧 Webhook Config: /set_webhook")
        
        # Executar servidor
        app.run(
            host='0.0.0.0',
            port=port,
            debug=False,
            use_reloader=False,
            threaded=True
        )
        
    except Exception as e:
        logger.error(f"❌ Erro crítico: {e}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main()
