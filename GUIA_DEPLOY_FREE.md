# 🆓 GUIA DE DEPLOY - PLANO GRATUITO DO RENDER

## 🎯 SOLUÇÃO PARA PLANO FREE

Como o plano gratuito do Render só permite **1 Web Service**, criamos uma solução unificada que roda **bot + dashboard no mesmo processo**.

## 📋 PASSOS PARA DEPLOY:

### 1. No Painel do Render:
- Clique em "Add new +" 
- Selecione **"Web Service"** (não Background Worker)
- Conecte ao repositório: `henrique-jfp/MaestroFin`

### 2. Configurações:
```
Name: maestrofin-unified
Environment: Python 3
Build Command: pip install -r requirements.txt  
Start Command: python unified_launcher.py
```

### 3. Environment Variables:
```
MAESTROFIN_MODE = unified
PYTHON_VERSION = 3.12.7
PYTHONUNBUFFERED = 1
RENDER_DEPLOY = true

# Suas variáveis secretas:
TELEGRAM_TOKEN = [seu_token]
GEMINI_API_KEY = [sua_key] 
DATABASE_URL = [sua_url_postgres]
GOOGLE_VISION_CREDENTIALS_JSON = [suas_credenciais]
# etc...
```

## 🔧 COMO FUNCIONA:

### Sistema Unificado:
- **Thread 1**: Bot do Telegram (background)
- **Thread 2**: Dashboard Flask (foreground)
- **Processo único**: Mantém ambos rodando simultaneamente

### Vantagens:
✅ Compatível com plano gratuito  
✅ Dashboard e bot funcionam juntos
✅ Analytics em tempo real
✅ OCR para documentos diretos

## 📊 RESULTADO ESPERADO:

1. **Dashboard**: Disponível na URL do Render com dados reais
2. **Bot**: Funcionando no Telegram com OCR direto
3. **Analytics**: Dados coletados em tempo real no PostgreSQL

## ⚠️ IMPORTANTE:

- Use `render_unified.yaml` como referência
- O `unified_launcher.py` gerencia ambos os serviços
- Em produção usa threading, localmente usa multiprocessing
- Dashboard fica disponível na porta do Render (geralmente 10000)
