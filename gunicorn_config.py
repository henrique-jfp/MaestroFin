#!/usr/bin/env python3
"""
⚡ Configuração Gunicorn para Render
"""
import os
import multiprocessing

# Configurações básicas
bind = f"0.0.0.0:{os.environ.get('PORT', 10000)}"
workers = min(4, (multiprocessing.cpu_count() * 2) + 1)
worker_class = "gevent"
worker_connections = 1000
timeout = 60
keepalive = 2
max_requests = 1000
max_requests_jitter = 100

# Logs
accesslog = "-"
errorlog = "-"
loglevel = "info"
capture_output = True

# Process names
proc_name = "maestrofin"

# Worker recycling
preload_app = True
