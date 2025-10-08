"""WSGI entrypoint para Render / Gunicorn.
Mantém compatibilidade mesmo se estrutura mudar.
"""
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Preferir APP principal do dashboard
try:
    from analytics.dashboard_app import app  # type: ignore
except Exception:
    # Fallback para wrapper criado
    from app import app  # type: ignore  # noqa: F401

# Exposto como variável 'app' para gunicorn: wsgi:app
