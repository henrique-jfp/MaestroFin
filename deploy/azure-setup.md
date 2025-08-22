# 🔷 DEPLOY NO AZURE - PASSO A PASSO

## 🎯 **PRÉ-REQUISITOS:**
1. ✅ Conta Microsoft com GitHub Student Developer Pack
2. ✅ Código no GitHub (✅ JÁ TEMOS!)
3. ✅ Azure for Students ativado

---

## 📋 **PASSO 1: ATIVAR AZURE FOR STUDENTS**

### **🔗 Acesse:**
https://azure.microsoft.com/free/students/

### **✅ Ativar conta:**
1. Login com conta Microsoft/GitHub
2. Verificar elegibilidade (Student Pack)
3. Ativar $100 créditos/mês

---

## 📋 **PASSO 2: CRIAR AZURE CONTAINER INSTANCE**

### **🖥️ No Portal Azure:**
1. **Buscar:** "Container Instances" 
2. **Clicar:** "Create"
3. **Configurar:**
   - **Resource Group:** `maestrofin-rg`
   - **Container Name:** `maestrofin-bot`
   - **Region:** `East US` (mais barato)
   - **Image:** `python:3.12-slim`

### **⚙️ Configurações Avançadas:**
- **CPU:** 0.5 cores
- **Memory:** 1 GB
- **OS Type:** Linux
- **Restart Policy:** Always

---

## 📋 **PASSO 3: PREPARAR DOCKERFILE**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Criar diretórios necessários
RUN mkdir -p database static templates credentials

# Variáveis de ambiente
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

CMD ["python", "bot.py"]
```

---

## 📋 **PASSO 4: CONFIGURAR VARIÁVEIS DE AMBIENTE**

### **🔒 No Azure Container Instance:**
```bash
TELEGRAM_BOT_TOKEN=seu_token_aqui
GEMINI_API_KEY=sua_key_aqui
DATABASE_URL=sqlite:///app/database/maestrofin.db
ENVIRONMENT=production
```

---

## 💰 **CUSTOS ESTIMADOS:**
- **Container Instance (0.5 CPU, 1GB):** ~$15/mês
- **Storage:** ~$2/mês  
- **Bandwidth:** ~$1/mês
- **TOTAL:** ~$18/mês (**COBERTO pelos $100 créditos!**)

---

## 🚀 **DEPLOY AUTOMÁTICO:**
1. Push para GitHub
2. Azure automaticamente redeploy
3. Bot funcionando 24/7!
