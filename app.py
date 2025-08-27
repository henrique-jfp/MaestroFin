"""
WSGI entrypoint para Render.
Render detectou gunicorn e tentou carregar 'app:app'.
Este arquivo expõe a variável 'app' apontando para a aplicação Flask integrada
(dashboard + webhook do bot) usando o unified_launcher. 

Se TELEGRAM_TOKEN não estiver definido, apenas o dashboard sobe em modo degradado.
"""
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from unified_launcher import create_integrated_app
    app = create_integrated_app()
    logger.info("✅ WSGI app criada via unified_launcher.create_integrated_app()")
except Exception as e:  # Fallback estrito: só dashboard
    logger.error(f"❌ Falha ao criar app integrada: {e}. Usando fallback somente dashboard.")
    try:
        from analytics.dashboard_app import app  # type: ignore
        logger.info("✅ Fallback dashboard carregado")
    except Exception as e2:
        logger.critical(f"🔥 Falha também no fallback dashboard: {e2}")
        raise

# Opcional: health endpoint rápido para diagnóstico inicial
@app.route('/_wsgi_health')
def _wsgi_health():  # pragma: no cover
    return {
        "status": "ok",
        "bot_enabled": bool(os.environ.get('TELEGRAM_TOKEN')),
        "pid": os.getpid(),
    }, 200
