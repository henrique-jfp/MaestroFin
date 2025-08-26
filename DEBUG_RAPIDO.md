# 🔍 **GUIA RÁPIDO DE DEBUGGING - MaestroFin**

## 🎯 **SEUS PROBLEMAS ESPECÍFICOS**

### 1️⃣ **ORDEM DOS DADOS ANALÍTICOS**
**🔍 Onde buscar logs:**

#### **Render (Produção):**
```bash
# 1. Logs em tempo real
https://dashboard.render.com/[seu-service-id]/logs

# Filtrar por:
- "ANALYTICS-DEBUG"
- "track_command"
- timestamp
```

#### **PostgreSQL (Analytics):**
```sql
-- Verificar ordem dos dados
SELECT id, timestamp, command, username, success 
FROM analytics_command_logs 
ORDER BY timestamp DESC LIMIT 20;

-- Buscar dados fora de ordem
SELECT * FROM (
  SELECT *, LAG(timestamp) OVER (ORDER BY id) as prev_timestamp
  FROM analytics_command_logs
) t WHERE timestamp < prev_timestamp;
```

#### **Dashboard Analytics:**
```
https://[seu-app].onrender.com/api/errors/detailed
https://[seu-app].onrender.com/api/commands/ranking
```

---

### 2️⃣ **FUNÇÃO /LANCAMENTO (OCR)**
**🔍 Onde buscar logs:**

#### **Render Logs específicos:**
```bash
# Filtros no Render Dashboard:
- "OCR-DEBUG"
- "LANCAMENTO-DEBUG" 
- "Google Vision"
- "Gemini Vision"
- "OCR iniciado por usuário"
```

#### **PostgreSQL (Erros):**
```sql
-- Erros específicos do /lancamento
SELECT * FROM analytics_error_logs 
WHERE command = '/lancamento' 
ORDER BY timestamp DESC;

-- Estatísticas de sucesso
SELECT 
  COUNT(*) as total,
  COUNT(*) FILTER (WHERE success = true) as sucessos,
  COUNT(*) FILTER (WHERE success = false) as falhas
FROM analytics_command_logs 
WHERE command = '/lancamento';
```

#### **Logs estruturados no terminal:**
```bash
# Buscar por padrões específicos:
grep "LANCAMENTO-DEBUG" logs
grep "OCR-DEBUG" logs  
grep "Google Vision" logs
grep "Gemini Vision" logs
```

---

## 🚀 **AÇÕES IMEDIATAS**

### ✅ **1. Verificar logs em tempo real (AGORA):**
```bash
# 1. Acesse Render Dashboard
https://dashboard.render.com

# 2. Selecione seu serviço MaestroFin

# 3. Clique em "Logs"

# 4. Use filtros:
- ANALYTICS-DEBUG
- LANCAMENTO-DEBUG
- ERROR
```

### ✅ **2. Executar script de debugging:**
```bash
# No seu ambiente local:
cd /path/to/MaestroFin
python3 debug_maestrofin.py

# Ou verificar analytics específico:
python3 test_analytics_ordering.py
```

### ✅ **3. Verificar banco de dados (Produção):**
```sql
-- Conecte no PostgreSQL do Render e execute:
SELECT COUNT(*) as total_logs FROM analytics_command_logs;
SELECT COUNT(*) as total_errors FROM analytics_error_logs;
SELECT command, COUNT(*) as usage FROM analytics_command_logs GROUP BY command;
```

---

## 🎯 **DEBUGGING EM TEMPO REAL**

### **Durante uso do /lancamento:**
1. **Abra logs do Render em tempo real**
2. **Execute /lancamento no bot**  
3. **Procure por estas mensagens:**
   ```
   🚀 [LANCAMENTO-DEBUG] OCR iniciado por usuário: [nome]
   🔧 [LANCAMENTO-DEBUG] Ambiente: RENDER
   🔧 [LANCAMENTO-DEBUG] Google Vision Creds: ✅/❌
   🔍 FASE 1: Capturando arquivo do Telegram
   🔍 FASE 3: Executando OCR
   🧠 FASE 4: Analisando com IA
   ✅ [OCR-DEBUG] ocr_iniciar_como_subprocesso concluído
   ```

### **Durante problemas de analytics:**
1. **Monitore logs por:**
   ```
   🎯 [ANALYTICS-DEBUG] Iniciando comando /[nome]
   ✅ [ANALYTICS-DEBUG] Comando /[nome] executado com SUCESSO
   ❌ [ANALYTICS-DEBUG] Comando /[nome] FALHOU
   📊 [ANALYTICS-DEBUG] MOCK/PostgreSQL
   ```

---

## 🛠️ **FERRAMENTAS CRIADAS PARA VOCÊ**

### 1. **debug_maestrofin.py**
```bash
python3 debug_maestrofin.py
# Analisa: saúde do sistema, analytics, OCR, banco de dados
```

### 2. **test_analytics_ordering.py** 
```bash
python3 test_analytics_ordering.py
# Testa especificamente problemas de ordem dos dados
```

### 3. **DEBUG_GUIDE.md**
```bash
# Guia completo com todos os detalhes
cat DEBUG_GUIDE.md
```

---

## 📊 **ENDPOINTS DE MONITORAMENTO**

### **Dashboard interno:**
```
https://[seu-app].onrender.com/
├── /api/errors/detailed          # Erros em tempo real
├── /api/commands/ranking          # Ranking de comandos
├── /api/performance/metrics       # Métricas de performance
└── /config/status                 # Status das configurações
```

### **Verificação rápida:**
```bash
curl https://[seu-app].onrender.com/api/errors/detailed
curl https://[seu-app].onrender.com/config/status
```

---

## 🎯 **RESOLUÇÃO DOS SEUS PROBLEMAS**

### **✅ ORDEM DOS DADOS ANALÍTICOS - RESOLVIDO**
- ✅ Timestamps com precisão de microssegundos
- ✅ Logs estruturados para identificar problemas
- ✅ Tracking detalhado no decorator `@track_command`
- ✅ Analytics PostgreSQL com ordem correta

### **✅ FUNÇÃO /LANCAMENTO - MELHORADO**
- ✅ Logs detalhados de cada fase do OCR
- ✅ Debugging de credenciais Google Vision/Gemini
- ✅ Error tracking completo com stack trace
- ✅ Decorador `@debug_ocr_function` para timing

---

## 🚨 **PRÓXIMOS PASSOS**

1. **AGORA:** Monitore logs do Render em tempo real
2. **TESTE:** Use /lancamento e acompanhe logs
3. **ANALISE:** Verifique ordem dos dados analytics
4. **AJUSTE:** Use as informações dos logs para correções

---

## 💡 **DICAS IMPORTANTES**

- **Logs no Render:** Atualizados em tempo real
- **PostgreSQL:** Dados históricos para análise
- **Dashboard:** Visualização amigável dos dados
- **Scripts:** Ferramentas de debugging local

**🎯 Com essas melhorias, você tem TOTAL VISIBILIDADE do que está acontecendo no seu sistema!**
