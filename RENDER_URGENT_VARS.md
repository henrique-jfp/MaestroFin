# 🚨 VARIÁVEIS URGENTES - RENDER CONFIG

## ❌ **Problemas Identificados nos Prints:**

### **1. Erro EMAIL (/contato)**
**Problema**: "Erro no servidor de e-mails"
**Solução**: Adicionar variáveis de email

### **2. Erro PIX (doação)**  
**Problema**: "minha chave PIX tirou uma folga"
**Solução**: Configurar PIX_KEY

### **3. Timeout Fatura**
**Problema**: "Timeout no download!"
**Solução**: Configurar GEMINI_API_KEY para melhor processamento

## 🔧 **VARIÁVEIS PARA ADICIONAR NO RENDER:**

### **📧 EMAIL (Necessário para /contato)**
```
EMAIL_HOST_USER = seu_login_brevo@smtp-brevo.com
EMAIL_HOST_PASSWORD = sua_senha_smtp_brevo  
SENDER_EMAIL = seu@email.com
EMAIL_RECEIVER = destino@email.com
```

### **💳 PIX (Necessário para doação)**
```
PIX_KEY = sua_chave_pix@email.com
```

### **🤖 IA (Recomendado para melhor performance)**
```
GEMINI_API_KEY = AIzaSyC...sua_key_completa
```

## 📋 **PASSO A PASSO NO RENDER:**

1. **Acesse seu Web Service no Render**
2. **Environment Tab** → **Add Environment Variable**
3. **Adicione uma por vez**:

```
Key: EMAIL_HOST_USER
Value: seu_login_brevo@smtp-brevo.com

Key: EMAIL_HOST_PASSWORD  
Value: sua_senha_smtp

Key: SENDER_EMAIL
Value: seu@email.com

Key: EMAIL_RECEIVER
Value: destino@email.com

Key: PIX_KEY
Value: sua_chave_pix@email.com

Key: GEMINI_API_KEY
Value: AIzaSyC...sua_key_gemini
```

## 🎯 **COMO OBTER AS CREDENCIAIS:**

### **📧 Para EMAIL (Brevo/SMTP):**
1. Crie conta gratuita no Brevo
2. SMTP & API → SMTP Keys
3. Copie login/senha SMTP

### **💳 Para PIX:**
1. Use sua chave PIX pessoal
2. Pode ser email, telefone ou chave aleatória

### **🤖 Para GEMINI:**
1. https://makersuite.google.com/app/apikey
2. Create API Key
3. Copie a chave

## ✅ **RESULTADO APÓS CONFIGURAÇÃO:**
- ✅ `/contato` funcionará (enviará emails)
- ✅ PIX aparecerá corretamente (doações)
- ✅ Faturas processarão melhor (menos timeouts)
- ✅ Dashboard analytics continuará funcionando

---
**🚨 Prioridade: EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, PIX_KEY**
