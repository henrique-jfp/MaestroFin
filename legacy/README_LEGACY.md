Este diretório armazena arquivos legados / não usados em produção atual.

Manter para referência histórica. Não apontar Procfile ou deploy para estes arquivos.

Arquivos migrados:
- unified_launcher.py (launcher anterior sem watchdog/timeout)
- render_launcher.py (arquitetura fila/queue)
- app_definitivo.py (duplicado de app.py)
- render_fix.py (script one-off de correção)
- fix_analytics_schema.py (script de migração BigInt manual)
- analytics/dashboard_app_render_fixed.py (removido – vazio)
- analytics/metrics.py (não referenciado – exemplos de métricas mock)
- advanced_config.py (não referenciado)

Caso precise reativar algo, mova de volta explicitamente e revise dependências.
