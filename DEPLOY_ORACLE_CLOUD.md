# 🚀 ORACLE CLOUD - PASSO A PASSO COMPLETO

Deploy do MaestroFin Bot na Oracle Cloud (Always Free) - 100% Gratuito 24/7

---

## 📋 **FASE 1: CRIAR CONTA ORACLE CLOUD (5 minutos)**

### **Passo 1.1: Registro**
1. Acesse: https://www.oracle.com/cloud/free/
2. Clique em **"Start for free"**
3. Preencha:
   - **Email:** Seu email (pode usar email de estudante)
   - **Country:** Brazil
   - **Cloud Account Name:** `maestrofin` (ou qualquer nome único)
4. Clique em **"Verify my email"**
5. Verifique seu email e clique no link de confirmação

### **Passo 1.2: Dados pessoais**
1. **Account Type:** Individual (pessoa física)
2. Preencha seus dados pessoais
3. **Mobile number:** Seu celular (vai receber SMS de verificação)
4. Verifique o SMS

### **Passo 1.3: Pagamento (NÃO COBRA!)**
1. **⚠️ IMPORTANTE:** Pede cartão mas **NÃO COBRA NADA**
2. É apenas verificação de identidade
3. Aceite usar cartão de débito ou crédito
4. Preencha dados do cartão
5. **Nenhuma cobrança será feita!**

### **Passo 1.4: Confirmação**
1. Aceite os termos
2. Clique em **"Start my free trial"**
3. Aguarde 1-2 minutos (processamento)
4. ✅ Conta criada!

---

## 🖥️ **FASE 2: CRIAR VM GRATUITA (10 minutos)**

### **Passo 2.1: Acessar Console**
1. Faça login em: https://cloud.oracle.com
2. Você verá o dashboard da Oracle Cloud

### **Passo 2.2: Criar Instância**
1. No menu superior, clique em **"☰"** (hambúrguer)
2. Vá em **"Compute"** → **"Instances"**
3. Clique no botão azul **"Create Instance"**

### **Passo 2.3: Configurar a VM**

**Nome da instância:**
```
maestrofin-bot
```

**Placement:**
- Deixe o padrão (availability domain selecionado)

**Image and Shape:**
1. Clique em **"Change Image"**
2. Selecione: **"Ubuntu"** → **"Canonical Ubuntu 22.04"**
3. Clique em **"Select Image"**

4. Clique em **"Change Shape"**
5. Selecione: **"Specialty and previous generation"** (na aba lateral)
6. Marque: **"VM.Standard.E2.1.Micro"** (Always Free Eligible)
   - 1 OCPU
   - 1 GB RAM
7. Clique em **"Select Shape"**

**Networking:**
- Deixe tudo padrão
- **⚠️ Certifique-se:** "Assign a public IPv4 address" está MARCADO

**Add SSH Keys:**
1. Selecione: **"Generate a key pair for me"**
2. Clique em **"Save Private Key"** (salve como `maestrofin-key.pem` na sua pasta Downloads)
3. Clique em **"Save Public Key"** (opcional, mas recomendado)

**Boot Volume:**
- Deixe padrão (50 GB é suficiente)

### **Passo 2.4: Criar!**
1. Role até o final
2. Clique no botão azul **"Create"**
3. Aguarde ~2 minutos (status vai de "Provisioning" para "Running")
4. ✅ VM criada!

### **Passo 2.5: Anotar IP Público**
1. Quando a instância estiver **"Running"** (bolinha verde)
2. Copie o **"Public IP address"**
3. Exemplo: `129.146.123.45`
4. **⚠️ GUARDE ESSE IP!**

---

## 🔐 **FASE 3: LIBERAR PORTAS (FIREWALL) (3 minutos)**

### **Passo 3.1: Abrir Security List**
1. Na tela da instância, clique em **"Subnet"** (em "Primary VNIC")
2. Clique na subnet (geralmente `subnet-xxx-vcn-xxx`)
3. Em **"Security Lists"**, clique na security list (geralmente `Default Security List`)

### **Passo 3.2: Adicionar Regra**
1. Clique em **"Add Ingress Rules"**
2. Preencha:
   - **Source CIDR:** `0.0.0.0/0`
   - **IP Protocol:** `All Protocols`
   - **Description:** `Allow all traffic`
3. Clique em **"Add Ingress Rules"**

**⚠️ IMPORTANTE:** Isso libera todas as portas. Para produção, você deveria liberar apenas as necessárias, mas para começar está OK.

---

## 🔗 **FASE 4: CONECTAR NA VM VIA SSH (5 minutos)**

### **Passo 4.1: Preparar a chave SSH (no seu PC)**

**No Linux/Mac:**
```bash
cd ~/Downloads
chmod 400 maestrofin-key.pem
```

**No Windows (use WSL ou Git Bash):**
```bash
cd /mnt/c/Users/SEU_USUARIO/Downloads
chmod 400 maestrofin-key.pem
```

### **Passo 4.2: Conectar**

Substitua `SEU_IP` pelo IP público que você anotou:

```bash
ssh -i maestrofin-key.pem ubuntu@SEU_IP
```

Exemplo:
```bash
ssh -i maestrofin-key.pem ubuntu@129.146.123.45
```

**Se perguntar "Are you sure you want to continue connecting?"**
→ Digite `yes` e Enter

✅ **Você está dentro da VM agora!**

---

## 🐍 **FASE 5: INSTALAR DEPENDÊNCIAS (5 minutos)**

### **Passo 5.1: Atualizar sistema**
```bash
sudo apt update && sudo apt upgrade -y
```

### **Passo 5.2: Instalar Python e ferramentas**
```bash
sudo apt install -y python3 python3-pip git nano
```

### **Passo 5.3: Instalar Node.js e PM2**
```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
sudo npm install -g pm2
```

### **Passo 5.4: Verificar instalação**
```bash
python3 --version  # Deve mostrar: Python 3.10.x ou superior
pm2 --version      # Deve mostrar: 5.x.x
```

---

## 📦 **FASE 6: CLONAR E CONFIGURAR O BOT (5 minutos)**

### **Passo 6.1: Clonar repositório**
```bash
cd ~
git clone https://github.com/henrique-jfp/MaestroFin.git
cd MaestroFin
```

### **Passo 6.2: Checkout na branch correta**
```bash
git checkout restore-v1.0.0
```

### **Passo 6.3: Criar arquivo .env**
```bash
nano .env
```

**Cole EXATAMENTE isso (Ctrl+Shift+V no terminal):**
```env
TELEGRAM_TOKEN=8161147760:AAHUcBMOXA-1EYMIKDLtNWtYavfS1ZQtL_E
DATABASE_URL=postgresql://postgres.piglbbeabppungajtwbn:abr30cxx1902lauraaws-0-sa-east-1.pooler.supabase.com:6543/postgres
GEMINI_API_KEY=AIzaSyBH_BPFhI1Lt3Qp1Skg9zadLVtOakfAnY
EMAIL_HOST_USER=911b48001@smtp-brevo.com
EMAIL_HOST_PASSWORD=xsmtspsib-763cca6c8d2334f2fae0d4ef0b61fc53b2cb23291e907196c4862c2c3198176e-fP5mjgSCJB9LsEqp
EMAIL_RECEIVER=vdmgerente@gmail.com
SENDER_EMAIL=vdmgerente@gmail.com
PIX_KEY=5040848d-ce38-48b1-8ebe-4185d9d019e4
GEMINI_MODEL_NAME=gemini-1.5-flash
MAESTROFIN_MODE=bot
```

**Salvar e sair:**
- Pressione `Ctrl+X`
- Pressione `Y` (yes)
- Pressione `Enter`

### **Passo 6.4: Instalar dependências Python**
```bash
pip3 install -r requirements.txt
```

⏳ **Aguarde 2-3 minutos** (vai instalar todas as bibliotecas)

---

## 🚀 **FASE 7: INICIAR O BOT (2 minutos)**

### **Passo 7.1: Iniciar com PM2**
```bash
pm2 start launcher.py --interpreter python3 --name maestrofin
```

### **Passo 7.2: Verificar se está rodando**
```bash
pm2 status
```

Você deve ver:
```
┌─────┬───────────────┬─────────┬─────────┬────────┐
│ id  │ name          │ status  │ restart │ uptime │
├─────┼───────────────┼─────────┼─────────┼────────┤
│ 0   │ maestrofin    │ online  │ 0       │ 5s     │
└─────┴───────────────┴─────────┴─────────┴────────┘
```

### **Passo 7.3: Ver logs em tempo real**
```bash
pm2 logs maestrofin
```

Você deve ver:
```
🚀 Iniciando Maestro Financeiro...
✅ Todas as variáveis essenciais estão configuradas
🤖 Modo FORÇADO: BOT (via MAESTROFIN_MODE=bot)
🤖 Iniciando bot do Telegram...
```

**Pressione `Ctrl+C` para sair dos logs** (bot continua rodando!)

### **Passo 7.4: Configurar auto-start (bot reinicia se VM reiniciar)**
```bash
pm2 startup
```

**Copie e execute o comando que aparecer** (algo como `sudo env PATH=...`)

Depois:
```bash
pm2 save
```

✅ **BOT ESTÁ RODANDO 24/7!**

---

## 🧪 **FASE 8: TESTAR O BOT**

1. Abra o Telegram no seu celular
2. Procure: `@MaestroFinBot` (ou o nome do seu bot)
3. Envie: `/start`
4. **O bot deve responder!** 🎉

---

## 🛠️ **COMANDOS ÚTEIS:**

**Ver status do bot:**
```bash
pm2 status
```

**Ver logs em tempo real:**
```bash
pm2 logs maestrofin
```

**Parar o bot:**
```bash
pm2 stop maestrofin
```

**Reiniciar o bot:**
```bash
pm2 restart maestrofin
```

**Atualizar código (depois de fazer push no GitHub):**
```bash
cd ~/MaestroFin
git pull
pm2 restart maestrofin
```

**Desconectar da VM (bot continua rodando):**
```bash
exit
```

---

## ✅ **CHECKLIST FINAL:**

- [ ] Conta Oracle Cloud criada
- [ ] VM `maestrofin-bot` criada e Running
- [ ] IP público anotado
- [ ] Conectado via SSH
- [ ] Python, PM2 instalados
- [ ] Repositório clonado
- [ ] Arquivo `.env` criado com variáveis
- [ ] Dependências instaladas
- [ ] Bot iniciado com PM2
- [ ] PM2 configurado para auto-start
- [ ] Bot respondendo `/start` no Telegram

---

## 🆘 **SE DER ERRO:**

**Erro ao conectar SSH:**
```bash
# Tente com -v para ver detalhes:
ssh -v -i maestrofin-key.pem ubuntu@SEU_IP
```

**Erro "Permission denied (publickey)":**
```bash
# Certifique-se que a chave tem permissão correta:
chmod 400 maestrofin-key.pem
```

**Bot não inicia (pm2 status = errored):**
```bash
# Ver logs de erro:
pm2 logs maestrofin --err
```

**Import erro (ModuleNotFoundError):**
```bash
# Reinstalar dependências:
cd ~/MaestroFin
pip3 install -r requirements.txt --force-reinstall
```

---

## 💰 **CUSTOS:**

- ✅ **$0.00/mês** - Totalmente gratuito PARA SEMPRE!
- ✅ **Sem limite de tempo** - Always Free tier nunca expira
- ✅ **750 horas/mês** - Suficiente para rodar 24/7 (720 horas)

---

**Criado em:** 17/11/2025  
**Por:** Henrique Freitas  
**Projeto:** MaestroFin Bot
