#!/usr/bin/env python3
"""
⚡ Configuração Gunicorn Ultra Robusta para Render
"""
import os
import multiprocessing

# Configurações básicas
bind = f"0.0.0.0:{os.environ.get('PORT', 10000)}"
# IMPORTANTE: manter apenas 1 worker para não duplicar estado de bot / threads
workers = 1
worker_class = "sync"  # simplifica interação com threads asyncio internas
timeout = 120
keepalive = 5
graceful_timeout = 60
# Desativamos reciclagem agressiva para preservar loop persistente; se quiser reciclar use max_requests em produção futura
# max_requests = 500
# max_requests_jitter = 50

# Logs
accesslog = "-"
errorlog = "-"
loglevel = "info"
capture_output = True

# Process names
proc_name = "maestrofin"

# Worker recycling - IMPORTANTE para SSL
preload_app = False  # evitar iniciar thread/event loop antes do fork
reload = False  # Sem hot reload em produção

# SSL/Connection management
worker_tmp_dir = "/dev/shm"  # Use memory for temp files

# Para debug
print(f"🚀 Gunicorn Config - Workers: {workers}, Class: {worker_class}, Preload: {preload_app}")
