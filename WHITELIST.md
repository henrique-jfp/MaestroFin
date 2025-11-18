# 🔐 Sistema de Whitelist - Open Finance

## 📋 Visão Geral

O sistema de whitelist permite **restringir o acesso ao Open Finance** apenas para usuários autorizados, mantendo o resto do bot público.

## 🎯 Quando Usar

✅ **Use whitelist quando:**
- Estiver no período trial da Pluggy (14 dias)
- Tiver licença acadêmica limitada
- Quiser controlar os custos da API
- Desenvolver/testar com dados reais

❌ **Não use whitelist quando:**
- Tiver plano Pluggy pago ilimitado
- Quiser abrir para todos os usuários
- Bot for completamente público

## ⚙️ Como Configurar

### 1️⃣ Descobrir seu Telegram ID

Envie `/start` para [@userinfobot](https://t.me/userinfobot) no Telegram:

```
📱 User Info:
Id: 6157591255
First name: Seu Nome
...
```

### 2️⃣ Configurar no Railway

**Opção A: Dashboard Railway**
1. Acesse seu projeto no Railway
2. Vá em **Variables**
3. Clique em **+ New Variable**
4. Nome: `PLUGGY_WHITELIST`
5. Valor: `6157591255` (seu ID)
6. Clique em **Add**
7. Railway fará redeploy automático

**Opção B: Múltiplos usuários**
```
PLUGGY_WHITELIST=6157591255,123456789,987654321
```

**Opção C: Desabilitar whitelist (todos podem usar)**
```
PLUGGY_WHITELIST=
```
(deixe vazio ou não configure)

### 3️⃣ Testar

1. **Você (autorizado)**: `/conectar_banco` → Funciona normalmente
2. **Outro usuário**: `/conectar_banco` → Vê mensagem:

```
🔒 Open Finance Restrito

Esta funcionalidade está temporariamente restrita durante 
o período de licença acadêmica.

✅ Você ainda pode usar:
• 📝 /adicionar - Lançamentos manuais
• 📊 /resumo - Visualizar relatórios
• 🎯 /metas - Gerenciar metas
• 🤖 /gerente - Assistente financeiro IA
• 💰 /investimentos - Cadastro manual

💡 Todas as outras funcionalidades do bot continuam disponíveis!
```

## 🔒 Comandos Protegidos

Quando a whitelist está ativa, apenas usuários autorizados podem:

- ✅ `/conectar_banco` - Conectar contas via Open Finance
- ✅ `/minhas_contas` - Ver contas conectadas
- ✅ `/sincronizar` - Sincronizar transações
- ✅ `/importar_transacoes` - Importar transações bancárias

**Comandos que continuam públicos:**
- ✅ `/start`, `/ajuda`, `/menu`
- ✅ `/adicionar`, `/editar`, `/deletar`
- ✅ `/resumo`, `/relatorio`
- ✅ `/metas`, `/investimentos` (manual)
- ✅ `/gerente`, `/gamificacao`
- ✅ Todos os outros comandos do bot

## 💡 Estratégia Recomendada

### Durante Trial (14 dias)
```bash
# Abrir para todos testarem
PLUGGY_WHITELIST=
```

### Após Trial (aguardando licença)
```bash
# Restringir apenas para você
PLUGGY_WHITELIST=6157591255
```

### Com Licença Acadêmica
```bash
# Você + orientador + banca (se necessário)
PLUGGY_WHITELIST=6157591255,123456789,987654321
```

### Plano Pago
```bash
# Remover restrição completamente
PLUGGY_WHITELIST=
```

## 📧 Licença Acadêmica Pluggy

### Template de Email

```
Assunto: Solicitação de Licença Acadêmica - Projeto TCC Gestão Financeira

Olá time Pluggy,

Meu nome é [SEU NOME], sou estudante de [SEU CURSO] na [SUA UNIVERSIDADE]
e desenvolvi um bot de gestão financeira pessoal usando a API da Pluggy 
como parte do meu TCC.

**Sobre o projeto:**
- Bot no Telegram com IA para análise financeira
- Integração Open Finance via Pluggy API
- Objetivo: democratizar acesso a gestão financeira inteligente
- Repositório: https://github.com/henrique-jfp/MaestroFin

**Solicitação:**
Gostaria de uma licença acadêmica com uso EXTREMAMENTE limitado:
- 1 usuário (apenas meu CPF: XXX.XXX.XXX-XX)
- 3-4 conexões bancárias máximo
- Apenas para demonstração e desenvolvimento do projeto acadêmico
- Período: até [DATA DEFESA TCC]

O trial de 14 dias foi fundamental para validar a integração. Posso 
compartilhar o código-fonte e resultados do projeto com vocês.

Existe algum programa de licença educacional ou partnership acadêmico?

Agradeço desde já a atenção!

Atenciosamente,
[SEU NOME]
[SEU EMAIL]
[SEU TELEFONE]
```

### Contatos Pluggy
- 📧 Email: [Buscar no site da Pluggy](https://pluggy.ai/contato)
- 💬 Suporte: chat no dashboard da Pluggy
- 🐦 Twitter/X: [@pluggyapi](https://twitter.com/pluggyapi)

## 🔍 Verificar se está Funcionando

### No Railway Logs
```bash
# Whitelist ativa
🔐 Open Finance restrito a 1 usuário(s) autorizado(s)

# Whitelist desabilitada
🌐 Open Finance disponível para TODOS os usuários (Trial Mode)
```

### Quando usuário não autorizado tenta usar
```bash
🚫 Usuário 987654321 NÃO autorizado a usar Open Finance
```

## 🆘 Troubleshooting

### Problema: Adicionei meu ID mas ainda não funciona
**Solução**: Verificar se copiou o ID corretamente (sem espaços, sem aspas)
```bash
# ❌ ERRADO
PLUGGY_WHITELIST="6157591255"
PLUGGY_WHITELIST= 6157591255

# ✅ CERTO
PLUGGY_WHITELIST=6157591255
```

### Problema: Whitelist não respeita múltiplos IDs
**Solução**: Usar vírgula SEM espaços
```bash
# ❌ ERRADO
PLUGGY_WHITELIST=6157591255, 123456789, 987654321

# ✅ CERTO
PLUGGY_WHITELIST=6157591255,123456789,987654321
```

### Problema: Quero desabilitar temporariamente
**Solução**: Deletar a variável ou deixar vazia
```bash
PLUGGY_WHITELIST=
```

## 📊 Monitoramento

Você pode monitorar acessos nos logs:
```bash
# Acesso autorizado
👤 Usuário 6157591255 iniciando conexão Open Finance

# Acesso bloqueado
🚫 Usuário 987654321 NÃO autorizado a usar Open Finance
```

---

**Dúvidas?** Abra uma issue no GitHub ou entre em contato.
