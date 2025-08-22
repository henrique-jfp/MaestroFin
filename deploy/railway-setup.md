# 🐳 RAILWAY - DEPLOY MAIS SIMPLES (RECOMENDADO PARA COMEÇAR)

## ✅ **POR QUE RAILWAY?**
- 🎯 **Mais fácil** que Azure
- 💰 **$5/mês GRÁTIS** (GitHub Student Pack)
- ⚡ **Deploy em 2 minutos**
- 🔄 **Auto-deploy** do GitHub
- 📊 **Dashboard** intuitivo

---

## 📋 **PASSO A PASSO COMPLETO:**

### **🔗 PASSO 1: CRIAR CONTA**
1. Acesse: https://railway.app
2. **Sign up with GitHub**
3. Conectar repositório `henrique-jfp/MaestroFin`

### **🚀 PASSO 2: DEPLOY AUTOMÁTICO**
1. **New Project** → **Deploy from GitHub**
2. Selecionar: `henrique-jfp/MaestroFin`
3. Railway detecta automaticamente Python
4. **Deploy!**

### **⚙️ PASSO 3: CONFIGURAR VARIÁVEIS**
No dashboard Railway:
```bash
TELEGRAM_BOT_TOKEN=seu_token_bot
GEMINI_API_KEY=sua_chave_gemini
GOOGLE_VISION_CREDENTIALS=conteudo_json_credentials
DATABASE_PATH=/app/database/maestrofin.db
ENVIRONMENT=production
PORT=8080
```

### **📁 PASSO 4: AJUSTAR ARQUIVOS**

**Criar `Procfile`:**
```
web: python bot.py
```

**Criar `railway.json`:**
```json
{
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "python bot.py",
    "healthcheckPath": "/health"
  }
}
```

---

## 💰 **CUSTOS:**
- **Railway:** $5/mês → **GRÁTIS** (Student Pack)
- **Uptime:** 24/7 sem sleep
- **CPU:** 0.5 vCPU
- **RAM:** 512MB (suficiente)
- **Storage:** 1GB

---

## 🎯 **VANTAGENS:**
✅ **Setup em 5 minutos**
✅ **Auto-deploy do Git**
✅ **Logs em tempo real**
✅ **99.9% uptime**
✅ **SSL automático**
✅ **Domain personalizado**

---

## 📊 **MONITORAMENTO:**
- Dashboard com métricas
- Logs em tempo real  
- CPU/RAM usage
- Deploy history
- Health checks
