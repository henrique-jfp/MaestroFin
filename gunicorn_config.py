#!/usr/bin/env python3
"""
🔥 CONFIGURAÇÃO GUNICORN DEFINITIVA - Zero Race Conditions
"""
import os

# Configurações básicas DEFINITIVAS
bind = f"0.0.0.0:{os.environ.get('PORT', 10000)}"

# 🔥 CRÍTICO: 1 worker para evitar estado duplicado
workers = 1
worker_class = "sync"  # OBRIGATÓRIO para threads
timeout = 180  # Mais tempo para inicialização
keepalive = 10
graceful_timeout = 60

# 🔥 APP LOADING - ZERO RACE CONDITIONS
preload_app = False  # NUNCA preload com estado global
lazy_app = True      # SEMPRE lazy loading
reload = False       # Sem hot reload

# 🔥 WORKER RECYCLING DESABILITADO
max_requests = 0           # Worker NUNCA recicla
max_requests_jitter = 0    # Zero jitter

# Logs melhorados
accesslog = "-"
errorlog = "-"
loglevel = "info"
capture_output = True

# Process naming
proc_name = "maestrofin_definitivo"

# Performance otimizada
worker_tmp_dir = "/dev/shm"  # RAM disk

# Debug info
print(f"� [DEFINITIVO] Workers: {workers}, Preload: {preload_app}, Lazy: {lazy_app}, MaxReq: {max_requests}")
