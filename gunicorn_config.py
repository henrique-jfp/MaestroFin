#!/usr/bin/env python3
"""
⚡ Configuração Gunicorn Ultra Robusta para Render
"""
import os
import multiprocessing

# Configurações básicas
bind = f"0.0.0.0:{os.environ.get('PORT', 10000)}"
workers = 2  # Reduzido para evitar sobrecarga de SSL connections
worker_class = "gevent"
worker_connections = 500  # Menos conexões para evitar SSL overload
timeout = 120  # Timeout maior para operações de DB
keepalive = 5   # Keepalive maior para conexões
max_requests = 500  # Menos requests por worker
max_requests_jitter = 50
graceful_timeout = 60

# Logs
accesslog = "-"
errorlog = "-"
loglevel = "info"
capture_output = True

# Process names
proc_name = "maestrofin"

# Worker recycling - IMPORTANTE para SSL
preload_app = True
reload = False  # Sem hot reload em produção

# SSL/Connection management
worker_tmp_dir = "/dev/shm"  # Use memory for temp files

# Para debug
print(f"🚀 Gunicorn Config - Workers: {workers}, Connections: {worker_connections}")
