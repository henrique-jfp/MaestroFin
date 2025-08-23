# 🎼 MAESTROFIN - GUIA DE PRODUÇÃO 🎼

## 📋 ÍNDICE
- [🚀 Como Funciona o Deploy](#como-funciona-o-deploy)
- [✏️ Como Alterar o Bot Online](#como-alterar-o-bot-online)
- [🛑 Como Tirar o Bot do Ar](#como-tirar-o-bot-do-ar)
- [📊 Monitoramento](#monitoramento)
- [⚠️ Controle de Custos](#controle-de-custos)
- [🔧 Comandos Úteis](#comandos-úteis)
- [🆘 Resolução de Problemas](#resolução-de-problemas)

---

## 🚀 Como Funciona o Deploy

### 🔄 **Fluxo Automático:**
```
Código Local → GitHub → Railway → Bot Online
     ↓            ↓         ↓         ↓
   git push   webhook   build    restart
```

### ✅ **SIM, é automático!** 
- **Toda alteração** que você fizer e enviar para o GitHub **altera o bot online**
- **Não precisa** fazer nada manual no Railway
- O deploy acontece **automaticamente** em ~2-3 minutos

---

## ✏️ Como Alterar o Bot Online

### 📝 **Passo a Passo:**

#### 1. **Fazer Alterações Locais**
```bash
# Edite os arquivos que quiser (bot.py, handlers, etc.)
# Exemplo: alterar uma mensagem, adicionar comando, etc.
```

#### 2. **Testar Localmente (Opcional mas Recomendado)**
```bash
# Ative o ambiente virtual
source venv/bin/activate

# Rode localmente para testar
python bot.py
```

#### 3. **Enviar para GitHub**
```bash
# Adicionar arquivos alterados
git add .

# Fazer commit com descrição
git commit -m "✨ Adicionar novo comando /exemplo"

# Enviar para GitHub (isso dispara o deploy automático)
git push origin main
```

#### 4. **Aguardar Deploy Automático**
```bash
# Ver logs do deploy em tempo real
railway logs

# Verificar se está rodando
railway status
```

### 🎯 **Exemplos de Alterações Comuns:**

#### **Adicionar Novo Comando:**
```python
# Em bot.py ou em um handler
async def novo_comando(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🆕 Novo comando funcionando!")

# Adicionar ao application
application.add_handler(CommandHandler("novo", novo_comando))
```

#### **Alterar Mensagens:**
```python
# Trocar qualquer texto nas mensagens
await update.message.reply_text("📝 Texto alterado!")
```

#### **Adicionar Nova Funcionalidade:**
```python
# Criar arquivo novo_handler.py
# Importar e adicionar aos handlers principais
```

---

## 🛑 Como Tirar o Bot do Ar

### 🚨 **EMERGÊNCIA - Parar Imediatamente:**

#### **Método 1: Via Railway CLI (Mais Rápido)**
```bash
# Pausar o serviço
railway service disconnect

# OU suspender deployment
railway down
```

#### **Método 2: Via Dashboard Railway**
1. Acesse: https://railway.app/dashboard
2. Entre no projeto **MaestroFinanceiro**
3. Clique no serviço
4. Clique **"Pause Service"** ou **"Delete"**

#### **Método 3: Quebrar o Código (Última Opção)**
```bash
# Adicionar erro proposital no launcher_railway.py
echo "raise Exception('Bot pausado manualmente')" >> launcher_railway.py
git add . && git commit -m "🛑 Pausar bot" && git push origin main
```

### 🔄 **Para Reativar:**
```bash
# Método 1:
railway service connect

# Método 2: Via dashboard - clique "Resume"

# Método 3: Reverter commit com erro
git revert HEAD
git push origin main
```

---

## 📊 Monitoramento

### 📈 **URLs Importantes:**
- **Bot Status:** https://maestrofinanceiro-production.up.railway.app
- **Dashboard Analytics:** https://maestrofinanceiro-production.up.railway.app/dashboard
- **Railway Dashboard:** https://railway.app/project/05fcf117-4242-4545-bda4-239d50b01abe

### 🔍 **Comandos de Monitoramento:**
```bash
# Ver logs em tempo real
railway logs

# Status do deployment
railway status

# Informações do projeto
railway info

# Uso de recursos
railway metrics
```

### 📱 **Teste Manual do Bot:**
1. Abrir Telegram
2. Procurar seu bot
3. Enviar `/start`
4. Verificar se responde normalmente

---

## ⚠️ Controle de Custos

### 💰 **Railway - Plano Atual:**
- **$5/mês** por serviço ativo
- **500 horas/mês** incluídas
- Cobrança por hora adicional se passar

### 🚨 **Como Evitar Custos Excessivos:**

#### **Monitorar Uso:**
```bash
# Ver uso atual
railway metrics

# Ver faturamento
railway billing
```

#### **Definir Limites:**
1. Dashboard Railway → Settings
2. **Resource Limits**:
   - CPU: 1 vCPU (suficiente)
   - RAM: 512MB (suficiente)
   - Disk: 1GB (suficiente)

#### **Pausar em Emergência:**
```bash
# Se estiver gastando muito
railway service pause
```

---

## 🔧 Comandos Úteis

### 🛠️ **Railway CLI:**
```bash
# Login
railway login

# Status geral
railway status

# Logs
railway logs

# Variáveis de ambiente
railway variables

# Conectar ao banco
railway connect postgresql

# Pausar/Resume
railway service pause
railway service resume

# Deploy manual (normalmente automático)
railway up

# Informações do projeto
railway info
```

### 🐛 **Git/GitHub:**
```bash
# Ver status
git status

# Ver histórico
git log --oneline

# Reverter último commit
git revert HEAD

# Voltar para commit específico
git checkout <commit-hash>

# Ver diferenças
git diff
```

---

## 🆘 Resolução de Problemas

### ❌ **Bot Não Responde:**
```bash
# 1. Ver logs
railway logs

# 2. Verificar se está rodando
railway status

# 3. Reiniciar
railway service restart

# 4. Verificar variáveis
railway variables
```

### 🔧 **Erro de Build:**
```bash
# Ver logs de build
railway logs --build

# Verificar requirements.txt
# Verificar syntax dos arquivos Python
```

### 💸 **Custos Altos:**
```bash
# Ver métricas
railway metrics

# Pausar temporariamente
railway service pause

# Otimizar código (reduzir polling, memory leaks, etc.)
```

### 🗄️ **Problema no Banco:**
```bash
# Conectar ao PostgreSQL
railway connect postgresql

# Ver logs específicos do banco
railway logs | grep -i "database\|postgres\|sql"
```

---

## 📝 **Fluxo de Trabalho Recomendado:**

### 🔄 **Para Alterações Pequenas:**
1. Editar código local
2. `git add . && git commit -m "descrição"`
3. `git push origin main`
4. Aguardar 2-3 minutos
5. Testar no Telegram

### 🧪 **Para Alterações Grandes:**
1. Criar branch: `git checkout -b nova-feature`
2. Desenvolver e testar localmente
3. `git push origin nova-feature`
4. Fazer merge: `git checkout main && git merge nova-feature`
5. `git push origin main`

### 🚨 **Para Emergências:**
1. `railway service pause` (parar imediatamente)
2. Investigar problema
3. Corrigir código
4. `railway service resume`

---

## ⚡ **RESUMO RÁPIDO:**

### ✅ **Para Alterar Bot:**
```bash
# Editar arquivos → git add . → git commit -m "msg" → git push origin main
# Aguardar 2-3 min → Pronto!
```

### 🛑 **Para Parar Bot:**
```bash
railway service pause
```

### 🔄 **Para Reativar Bot:**
```bash
railway service resume
```

### 📊 **Para Monitorar:**
```bash
railway logs
railway status
```

---

**🎼 Lembre-se: O bot está conectado diretamente ao GitHub. Qualquer push na branch `main` altera o bot online automaticamente! 🎼**

---

## 🆘 **CONTATOS DE EMERGÊNCIA:**

- **Railway Support:** https://railway.app/help
- **Telegram Bot API:** https://core.telegram.org/bots/api
- **Este Arquivo:** Para referência rápida

**📅 Última atualização:** 23 de agosto de 2025
**🤖 Bot Status:** ONLINE - https://maestrofinanceiro-production.up.railway.app
