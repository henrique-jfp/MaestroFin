# 🚀 Como Configurar Whitelist no Railway (Passo a Passo)

## 📋 Preparação

### 1️⃣ Descubra seu Telegram ID
1. Abra o Telegram
2. Busque por `@userinfobot`
3. Envie `/start`
4. Copie o número que aparece em **"Id: XXXXXXX"**
   - Exemplo: `6157591255`

---

## ⚙️ Configuração no Railway

### Passo 1: Acesse o Dashboard
1. Entre em https://railway.app
2. Faça login
3. Clique no seu projeto **MaestroFin**

### Passo 2: Adicione a Variável
1. Clique na aba **Variables** (ou **Settings** > **Variables**)
2. Clique em **+ New Variable** (ou **+ Add Variable**)

### Passo 3: Configure a Whitelist

**Opção A: Apenas você**
```
Nome: PLUGGY_WHITELIST
Valor: 6157591255
```
(substitua pelo SEU ID)

**Opção B: Você + outras pessoas**
```
Nome: PLUGGY_WHITELIST
Valor: 6157591255,123456789,987654321
```
(IDs separados por vírgula, SEM espaços)

**Opção C: Abrir para todos (Trial)**
```
Nome: PLUGGY_WHITELIST
Valor: 
```
(deixe VAZIO ou não adicione a variável)

### Passo 4: Salvar
1. Clique em **Add** (ou **Save**)
2. Railway fará **redeploy automático** (aguarde 1-2 minutos)

---

## ✅ Verificar se Funcionou

### No Railway Logs (Deploy Logs)
Procure por uma dessas mensagens:

**✅ Whitelist ATIVA (restrito):**
```
🔐 Open Finance restrito a 1 usuário(s) autorizado(s)
```

**✅ Whitelist DESABILITADA (público):**
```
🌐 Open Finance disponível para TODOS os usuários (Trial Mode)
```

### No Bot Telegram

**Como usuário AUTORIZADO:**
1. Envie `/conectar_banco`
2. Deve ver a lista de bancos normalmente

**Como usuário NÃO autorizado:**
1. Envie `/conectar_banco`
2. Deve ver:
```
🔒 Open Finance Restrito

Esta funcionalidade está temporariamente restrita durante 
o período de licença acadêmica.

✅ Você ainda pode usar:
• 📝 /adicionar - Lançamentos manuais
• 📊 /resumo - Visualizar relatórios
...
```

---

## 🔄 Modificar Whitelist

### Adicionar novo usuário
1. Railway > Variables > PLUGGY_WHITELIST
2. Clique para **editar**
3. Adicione novo ID: `6157591255,NOVO_ID_AQUI`
4. Salve (redeploy automático)

### Remover usuário
1. Edite PLUGGY_WHITELIST
2. Remova o ID indesejado
3. Salve

### Desabilitar whitelist (abrir para todos)
1. **Opção A**: Edite PLUGGY_WHITELIST e deixe VAZIO
2. **Opção B**: Delete a variável PLUGGY_WHITELIST

---

## 🎯 Estratégia de Uso

### 📅 Linha do Tempo Recomendada

**Semana 1-2 (Trial Pluggy):**
```bash
PLUGGY_WHITELIST=    # Vazio - abrir para testar
```
- Deixe público para amigos/família testarem
- Valide funcionalidades
- Coletar feedback

**Fim do Trial (dia 12-14):**
```bash
PLUGGY_WHITELIST=6157591255    # Só você
```
- Restringir apenas para você
- Enviar email para Pluggy solicitando licença acadêmica

**Aguardando Resposta (2-4 semanas):**
```bash
PLUGGY_WHITELIST=6157591255    # Continuar restrito
```
- Manter restrito enquanto negocia
- Demonstrar projeto para orientador/banca

**Licença Acadêmica Aprovada:**
```bash
# Opção 1: Continuar restrito (1 CPF)
PLUGGY_WHITELIST=6157591255

# Opção 2: Abrir para demonstrações (orientador + banca)
PLUGGY_WHITELIST=6157591255,123456789,987654321
```

**Defesa TCC / Fim do Projeto:**
- Decidir se mantém ou desativa Open Finance
- Se desativar: remover credenciais Pluggy do Railway

---

## 🆘 Problemas Comuns

### ❌ Problema: "Adicionei meu ID mas ainda diz que está restrito"

**Causa**: ID copiado errado ou com espaços

**Solução:**
1. Verifique no @userinfobot se copiou o ID correto
2. Vá no Railway > Variables > PLUGGY_WHITELIST
3. Confira se NÃO tem:
   - ❌ Espaços: ` 6157591255`
   - ❌ Aspas: `"6157591255"`
   - ❌ Colchetes: `[6157591255]`
4. Deve ser APENAS os números: `6157591255`

### ❌ Problema: "Mudei a variável mas não atualizou"

**Causa**: Railway não fez redeploy

**Solução:**
1. Railway > Deployments
2. Clique nos 3 pontinhos do último deploy
3. Clique em **Redeploy**
4. Aguarde 1-2 minutos

### ❌ Problema: "Logs não mostram mensagem de whitelist"

**Causa**: Logs antigos ou Railway ainda fazendo deploy

**Solução:**
1. Railway > Deployments > Ver deploy mais recente
2. Clicar em **View Logs**
3. Procurar por:
   - `🔐 Open Finance restrito` OU
   - `🌐 Open Finance disponível`
4. Se não aparecer: aguardar deploy terminar

---

## 📧 Próximo Passo: Email para Pluggy

Após configurar a whitelist e testar, prepare o email para Pluggy:

**Quando enviar:**
- ✅ Dias 12-14 do trial (antes de expirar)
- ✅ Já testou e validou todas funcionalidades
- ✅ Tem repositório GitHub atualizado

**Template:** Ver arquivo `WHITELIST.md` seção "Licença Acadêmica Pluggy"

**Aumentar chances de sucesso:**
- 📸 Screenshots do bot funcionando
- 🎥 Vídeo curto de demonstração (1-2 min)
- 📊 Estatísticas de uso (quantos testes, transações, etc)
- 🎓 Mencionar universidade e orientador
- 🌟 Destacar que é open source e educacional

---

**Dúvidas?** Consulte o arquivo `WHITELIST.md` para documentação completa.
