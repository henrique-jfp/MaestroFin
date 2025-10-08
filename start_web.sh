#!/usr/bin/env bash
set -euo pipefail

echo "[MaestroFin] Iniciando serviço web com Gunicorn..."
# Garantir que a PORT do Render esteja definida
: "${PORT:=10000}"

# Log de ambiente mínimo
echo "PORT=${PORT} PYTHONUNBUFFERED=${PYTHONUNBUFFERED:-}" 

# Executar Gunicorn apontando para wsgi:app
exec gunicorn wsgi:app -c gunicorn_config.py --log-file -
