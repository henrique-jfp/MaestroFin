# 🚀 GUIA COMPLETO DE DEPLOY GRATUITO - MAESTROFIN

## 🎯 **OPÇÃO RECOMENDADA: RAILWAY (MAIS FÁCIL)**

### **📋 CHECKLIST PRÉ-DEPLOY:**
- ✅ Código no GitHub (henrique-jfp/MaestroFin)
- ✅ GitHub Student Developer Pack ativo
- ✅ Token do Bot Telegram
- ✅ API Key do Google Gemini
- ✅ Credentials do Google Vision

---

## 🐳 **PASSO A PASSO RAILWAY:**

### **🔗 1. CRIAR CONTA RAILWAY:**
1. **Acesse:** https://railway.app
2. **Clique:** "Start a New Project"
3. **Login:** "Continue with GitHub"
4. **Autorize** Railway a acessar seus repositórios

### **📦 2. DEPLOY DO PROJETO:**
1. **New Project** → **Deploy from GitHub repo**
2. **Selecionar:** `henrique-jfp/MaestroFin`
3. Railway detecta automaticamente Python
4. **Deploy automático iniciará!**

### **⚙️ 3. CONFIGURAR VARIÁVEIS DE AMBIENTE:**

No painel Railway, vá em **Variables** e adicione:

```bash
# Token do Bot Telegram
TELEGRAM_BOT_TOKEN=sua_token_aqui

# API do Google Gemini
GEMINI_API_KEY=sua_chave_gemini

# Credenciais Google Vision (conteúdo do JSON)
GOOGLE_VISION_CREDENTIALS={"type":"service_account",...}

# Configurações de produção
ENVIRONMENT=production
DATABASE_PATH=/app/database/maestrofin.db
PYTHONPATH=/app
PYTHONUNBUFFERED=1

# Porta (Railway define automaticamente)
PORT=8080
```

### **🎯 4. VERIFICAR DEPLOY:**
1. **Logs:** Verifique se não há erros
2. **Health Check:** Acesse URL do projeto + `/health`
3. **Bot:** Teste no Telegram

---

## 💰 **CUSTOS RAILWAY:**
- **Plano Hobby:** $5/mês
- **Com GitHub Student Pack:** **GRÁTIS!**
- **Recursos:** 512MB RAM, 1GB Storage
- **Uptime:** 24/7 sem sleep

---

## 🔷 **ALTERNATIVA: MICROSOFT AZURE**

### **📋 PREPARATIVOS:**
1. **Ativar Azure for Students:** https://azure.microsoft.com/free/students/
2. **Créditos:** $100/mês GRÁTIS

### **🚀 DEPLOY AZURE:**
1. **Container Instances** → Create
2. **Resource Group:** `maestrofin-rg`
3. **Container Name:** `maestrofin-bot`
4. **Image Source:** Docker Hub
5. **Image:** `python:3.12-slim`
6. **CPU:** 0.5 cores, **Memory:** 1 GB

### **⚙️ CONFIGURAÇÃO AZURE:**
- **Command:** `python bot_production.py`
- **Port:** 8080
- **Environment Variables:** (mesmas do Railway)

### **💰 CUSTOS AZURE:**
- **Container Instance:** ~$18/mês
- **Coberto pelos $100 créditos!**

---

## 🔍 **MONITORAMENTO:**

### **📊 Railway Dashboard:**
- **Metrics:** CPU, RAM, Network
- **Logs:** Real-time
- **Deployments:** Histórico
- **Health Checks:** Status

### **🔧 URLs Importantes:**
- **Projeto:** https://railway.app/dashboard
- **Health Check:** `[sua-url]/health`
- **Status:** `[sua-url]/`

---

## 🛠️ **TROUBLESHOOTING:**

### **❌ Deploy Falhou:**
```bash
# Verificar logs no Railway
# Problema comum: variáveis de ambiente

# Soluções:
1. Verificar se todas as env vars estão definidas
2. Checar se o TELEGRAM_BOT_TOKEN está correto
3. Verificar se GEMINI_API_KEY é válida
```

### **❌ Bot Não Responde:**
```bash
# Verificar:
1. Token do bot válido
2. Bot adicionado ao grupo (se aplicável)  
3. API do Gemini configurada
4. Health check funcionando
```

### **❌ Erro de Permissões:**
```bash
# Verificar:
1. Google Vision credentials corretas
2. APIs habilitadas no Google Cloud
3. Service account com permissões
```

---

## ⚡ **COMANDOS DE VERIFICAÇÃO:**

### **🔍 Testar Health Check:**
```bash
curl https://sua-url-railway.up.railway.app/health
# Deve retornar: {"status": "healthy", ...}
```

### **🤖 Testar Bot:**
```
/start - no Telegram
/help - verificar comandos
/perfil - testar gamificação
```

---

## 📚 **PRÓXIMOS PASSOS APÓS DEPLOY:**

1. **✅ Bot funcionando 24/7**
2. **📊 Monitorar métricas** 
3. **🔄 Auto-deploy** ativo (push para Git = deploy automático)
4. **🎯 Adicionar novos recursos**
5. **📈 Escalar conforme necessário**

---

## 🎉 **RESULTADO FINAL:**

### **✨ BENEFÍCIOS ALCANÇADOS:**
- 🚀 **Bot funcionando 24/7**
- 💰 **Hospedagem GRATUITA** 
- ⚡ **Deploy automático**
- 📊 **Monitoramento integrado**
- 🔒 **SSL automático**
- 🌐 **URL personalizada**

**🎊 SEU BOT ESTARÁ ONLINE E FUNCIONAL!**

---

## 📞 **SUPORTE:**

**Railway:** https://docs.railway.app
**Azure:** https://docs.microsoft.com/azure
**GitHub Student Pack:** https://education.github.com/pack

**🚀 VAMOS COLOCAR O MAESTROFIN NO AR! 🚀**
