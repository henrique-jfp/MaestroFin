# 🔍 **GUIA COMPLETO DE DEBUGGING - MaestroFin**

## 📋 **ÍNDICE**
1. [Locais de Logs do Sistema](#1-locais-de-logs-do-sistema)
2. [Problemas Específicos](#2-problemas-específicos)
3. [Estratégias de Debugging](#3-estratégias-de-debugging)
4. [Ferramentas de Monitoramento](#4-ferramentas-de-monitoramento)
5. [Comandos Úteis](#5-comandos-úteis)

---

## 1. **LOCAIS DE LOGS DO SISTEMA**

### 🌐 **1.1 Render (Produção)**
```bash
# Logs principais do serviço
https://dashboard.render.com/web/[seu-service-id]/logs

# Tipos de logs disponíveis:
- Application logs (stdout/stderr)
- Deploy logs 
- Build logs
- Error logs
```

### 📊 **1.2 PostgreSQL Analytics (Produção)**
```sql
-- Logs de erros detalhados
SELECT * FROM analytics_error_logs 
ORDER BY timestamp DESC LIMIT 50;

-- Logs de comandos
SELECT * FROM analytics_command_logs 
WHERE command = '/lancamento' 
ORDER BY timestamp DESC LIMIT 20;

-- Logs de usuários ativos
SELECT * FROM analytics_daily_users 
ORDER BY date DESC LIMIT 10;
```

### 💾 **1.3 Arquivos de Log Local**
```bash
# Analytics local (se executando localmente)
./analytics.db

# Logs de dashboard handler
./dashboard_handler.log

# Cache de logs Python
./logs/
```

### 🐍 **1.4 Logs Python (Stdout/Stderr)**
```python
# Configurações de logging em:
- bot.py (linha 227)
- unified_launcher.py (linha 15)
- config.py (linha 7)
- analytics/dashboard_app.py (linha 16)
```

---

## 2. **PROBLEMAS ESPECÍFICOS**

### 🧾 **2.1 Função /lancamento (OCR)**
**Arquivos com logs relevantes:**
```bash
gerente_financeiro/ocr_handler.py      # OCR principal
gerente_financeiro/manual_entry_handler.py  # Entrada manual
bot.py (linhas 240-255)               # Error handler global
```

**Logs específicos para /lancamento:**
```python
# No ocr_handler.py - adicionar logs detalhados:
logger.info(f"🔍 OCR iniciado para usuário {user_id}")
logger.debug(f"📄 Processando imagem: {file_info}")
logger.error(f"❌ Falha no OCR: {error}")
```

### 📊 **2.2 Dados Analíticos (Ordem)**
**Arquivos com logs relevantes:**
```bash
analytics/dashboard_app.py (linhas 160+)  # Queries de dados
analytics/bot_analytics.py               # Tracking
analytics/advanced_analytics.py          # Análise avançada
```

**Queries de debugging:**
```sql
-- Verificar ordem dos dados
SELECT command, timestamp, success 
FROM analytics_command_logs 
ORDER BY timestamp DESC;

-- Verificar integridade dos dados
SELECT COUNT(*) as total, 
       COUNT(DISTINCT user_id) as usuarios,
       DATE(timestamp) as dia
FROM analytics_command_logs 
GROUP BY DATE(timestamp)
ORDER BY dia DESC;
```

---

## 3. **ESTRATÉGIAS DE DEBUGGING**

### 🎯 **3.1 Debugging em Tempo Real (Produção)**

#### **Opção A: Logs do Render em Tempo Real**
```bash
# Via Render Dashboard:
1. Acesse: https://dashboard.render.com
2. Selecione seu serviço MaestroFin
3. Aba "Logs" 
4. Use filtros: "Error", "Warning", "OCR", "lancamento"
```

#### **Opção B: Logs via PostgreSQL**
```sql
-- Criar view para debugging
CREATE OR REPLACE VIEW debug_recent_errors AS
SELECT 
    timestamp,
    error_type,
    error_message,
    user_id,
    command,
    stack_trace
FROM analytics_error_logs 
WHERE timestamp >= NOW() - INTERVAL '24 hours'
ORDER BY timestamp DESC;
```

### 🔧 **3.2 Debugging Local**

#### **Executar com logs detalhados:**
```bash
# Modo debug completo
export MAESTROFIN_DEBUG=true
export LOGGING_LEVEL=DEBUG
python3 unified_launcher.py
```

#### **Testar componentes individualmente:**
```bash
# Testar apenas OCR
python3 -c "
from gerente_financeiro.ocr_handler import process_receipt_image
# Teste específico
"

# Testar apenas analytics
python3 test_analytics.py

# Testar apenas dashboard
python3 analytics/dashboard_app.py
```

---

## 4. **FERRAMENTAS DE MONITORAMENTO**

### 📈 **4.1 Dashboard Analytics Interno**
```
URL: https://[seu-app].onrender.com/
Endpoints úteis:
- /api/errors/detailed          # Erros detalhados
- /api/commands/ranking         # Ranking de comandos
- /api/performance/metrics      # Métricas de performance
- /config/status               # Status das configurações
```

### 🗄️ **4.2 Acesso Direto ao PostgreSQL**
```bash
# Via psql (se tiver acesso)
psql $DATABASE_URL

# Queries essenciais:
\dt analytics*                  # Listar tabelas analytics
SELECT * FROM analytics_error_logs WHERE error_message LIKE '%lancamento%';
SELECT * FROM analytics_command_logs WHERE command = '/lancamento' ORDER BY timestamp DESC LIMIT 10;
```

### 🔍 **4.3 Logs Estruturados**
```python
# Adicionar ao seu código de debugging:
import json
import logging

# Logger estruturado
def log_structured(level, component, action, data=None, error=None):
    log_data = {
        'timestamp': datetime.now().isoformat(),
        'component': component,
        'action': action,
        'data': data,
        'error': str(error) if error else None
    }
    getattr(logging, level.lower())(json.dumps(log_data))

# Uso:
log_structured('INFO', 'OCR', 'processing_start', {'user_id': user_id})
log_structured('ERROR', 'OCR', 'processing_failed', error=e)
```

---

## 5. **COMANDOS ÚTEIS**

### 🚨 **5.1 Monitoramento em Tempo Real**
```bash
# Seguir logs do Render (via CLI se disponível)
render logs --tail --service [service-name]

# Monitorar analytics via psql
watch -n 5 'psql $DATABASE_URL -c "SELECT COUNT(*) FROM analytics_error_logs WHERE timestamp > NOW() - INTERVAL '\''1 hour'\'';"'
```

### 📊 **5.2 Análise de Performance**
```sql
-- Comandos mais lentos
SELECT command, AVG(execution_time) as avg_time, COUNT(*) as usage_count
FROM analytics_command_logs 
WHERE timestamp >= NOW() - INTERVAL '7 days'
GROUP BY command 
ORDER BY avg_time DESC;

-- Usuários com mais erros
SELECT user_id, COUNT(*) as error_count
FROM analytics_error_logs 
WHERE timestamp >= NOW() - INTERVAL '24 hours'
GROUP BY user_id 
ORDER BY error_count DESC;
```

### 🔧 **5.3 Debugging Específico**

#### **Para /lancamento:**
```python
# Adicionar ao ocr_handler.py:
@debug_decorator
async def process_receipt_image(image_data, user_id):
    logger.info(f"🔍 [DEBUG] OCR iniciado para usuário {user_id}")
    logger.debug(f"📄 [DEBUG] Tamanho da imagem: {len(image_data)} bytes")
    
    try:
        # ... processamento ...
        logger.info(f"✅ [DEBUG] OCR concluído com sucesso")
    except Exception as e:
        logger.error(f"❌ [DEBUG] Falha no OCR: {e}", exc_info=True)
        raise
```

#### **Para Analytics:**
```python
# Adicionar ao bot_analytics.py:
def track_command(command, user_id, success=True, execution_time=None, error=None):
    logger.debug(f"📊 [DEBUG] Tracking: {command} | User: {user_id} | Success: {success}")
    
    if not success and error:
        logger.error(f"❌ [DEBUG] Comando falhou: {command} | Erro: {error}")
```

---

## 6. **AÇÕES IMEDIATAS RECOMENDADAS**

### ✅ **Para resolver seus problemas atuais:**

1. **Ativar logs detalhados:**
   ```bash
   # Adicionar variável no Render:
   LOGGING_LEVEL=DEBUG
   ```

2. **Verificar dados analytics:**
   ```sql
   SELECT * FROM analytics_command_logs 
   WHERE command = '/lancamento' 
   ORDER BY timestamp DESC LIMIT 10;
   ```

3. **Testar OCR isoladamente:**
   - Criar script de teste específico
   - Validar credenciais Google Vision
   - Verificar fallback Gemini

4. **Monitorar em tempo real:**
   - Usar dashboard analytics: `/api/errors/detailed`
   - Acompanhar logs do Render durante testes

---

## 🎯 **PRÓXIMOS PASSOS**
1. Implementar logs estruturados nos pontos críticos
2. Criar dashboard de debugging personalizado
3. Configurar alertas automáticos para erros críticos
4. Implementar health checks para componentes principais

---

**💡 Dica:** Use os logs do Render como fonte primária, mas complemente com analytics PostgreSQL para análise histórica e padrões de erro.
