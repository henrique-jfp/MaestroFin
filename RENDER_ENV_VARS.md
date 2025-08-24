# 🔧 VARIÁVEIS DE AMBIENTE - RENDER DEPLOY

## 🎯 **Variáveis OBRIGATÓRIAS para o Dashboard:**

### **1. Sistema (Automáticas)**
```bash
# ✅ O Render configura automaticamente:
PORT=10000                    # Porta do servidor (automática)
PYTHONUNBUFFERED=1           # Logs em tempo real
PYTHONDONTWRITEBYTECODE=1    # Não criar arquivos .pyc
```

### **2. Telegram Bot (Necessária)**
```bash
TELEGRAM_TOKEN=1234567890:ABCD...
# 📱 Token do seu bot do Telegram
# 🔗 Obtenha em: @BotFather
```

## 🎯 **Variáveis OPCIONAIS (para funcionalidades completas):**

### **3. AI/Gemini (Recomendado)**
```bash
GEMINI_API_KEY=AIzaSyC...
# 🤖 Para funcionalidades de IA
# 🔗 Obtenha em: https://makersuite.google.com/app/apikey

GEMINI_MODEL_NAME=gemini-1.5-flash
# 📋 Modelo do Gemini (padrão: gemini-1.5-flash)
```

### **4. Banco de Dados (Produção)**
```bash
DATABASE_URL=postgresql://user:pass@host:5432/db
# 🗄️ PostgreSQL para produção
# 📝 Para desenvolvimento usa SQLite (analytics.db)
```

### **5. Google Services (OCR)**
```bash
GOOGLE_APPLICATION_CREDENTIALS=credenciais/service-account-key.json
# 👁️ Para OCR (Google Vision API)
# 📁 Arquivo JSON das credenciais

GOOGLE_API_KEY=AIzaSyD...
# 🔍 Para pesquisas Google

GOOGLE_CSE_ID=1234567890abcdef
# 🔍 Custom Search Engine ID
```

### **6. Email (Notificações)**
```bash
SENDER_EMAIL=seu@email.com
EMAIL_HOST_USER=seu@gmail.com
EMAIL_HOST_PASSWORD=senha_app_gmail
EMAIL_RECEIVER=destino@email.com
# 📧 Para envio de relatórios
```

### **7. PIX (Pagamentos)**
```bash
PIX_KEY=seu@email.com
# 💳 Chave PIX para pagamentos
```

## 🎨 **Como Configurar no Render:**

### **Passo 1: Variáveis Mínimas (Dashboard funcional)**
```bash
TELEGRAM_TOKEN=seu_token_bot_telegram
```

### **Passo 2: No painel do Render**
1. Vá para seu Web Service
2. **Environment** → **Add Environment Variable**
3. Adicione as variáveis uma por uma:

```
Key: TELEGRAM_TOKEN
Value: 1234567890:ABCD-seu-token-aqui
```

### **Passo 3: Variáveis Avançadas (opcionais)**
```bash
# Para IA completa:
GEMINI_API_KEY=AIzaSyC...

# Para banco produção:
DATABASE_URL=postgresql://...

# Para OCR:
GOOGLE_APPLICATION_CREDENTIALS=credenciais/service-account-key.json
```

## 🚀 **Cenários de Deploy:**

### **🔰 MÍNIMO (apenas dashboard)**
```bash
TELEGRAM_TOKEN=seu_token
# ✅ Dashboard Analytics funcionando
# ❌ Sem IA, sem OCR, sem emails
```

### **⭐ RECOMENDADO (completo)**
```bash
TELEGRAM_TOKEN=seu_token
GEMINI_API_KEY=sua_key
DATABASE_URL=postgresql://...
# ✅ Dashboard + IA + Banco robusto
```

### **🚀 COMPLETO (todas funcionalidades)**
```bash
TELEGRAM_TOKEN=seu_token
GEMINI_API_KEY=sua_key
DATABASE_URL=postgresql://...
GOOGLE_APPLICATION_CREDENTIALS=credenciais/service-account-key.json
SENDER_EMAIL=seu@email.com
EMAIL_HOST_PASSWORD=senha
PIX_KEY=seu@pix.com
# ✅ Todas as funcionalidades ativas
```

## 💡 **Dicas Importantes:**

1. **🔰 Comece com MÍNIMO**: Só `TELEGRAM_TOKEN`
2. **📊 Dashboard funcionará**: Mesmo sem outras variáveis
3. **🔧 Adicione gradualmente**: Conforme precisar das funcionalidades
4. **🔒 Segurança**: Nunca commite tokens no código
5. **📱 Teste**: Deploy funcional mesmo com config mínima

---
**🎨 Para o dashboard analytics, você só precisa do TELEGRAM_TOKEN!**
