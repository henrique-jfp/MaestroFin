# Como Testar a Integração Pluggy OAuth

Este guia explica como usar o script automático para testar o fluxo completo de OAuth com a Pluggy.

## Pré-requisitos

1. **Variáveis de ambiente configuradas**
   
   Crie um arquivo `.env` na raiz do projeto com:
   ```bash
   PLUGGY_CLIENT_ID=seu_client_id_aqui
   PLUGGY_CLIENT_SECRET=seu_client_secret_aqui
   PLUGGY_REDIRECT_URI=https://maestrofin-production.up.railway.app/pluggy/callback
   ```

2. **Domínio cadastrado no Pluggy**
   
   No dashboard da Pluggy (https://dashboard.pluggy.ai):
   - Vá em **Settings → Allowed Origins**
   - Adicione: `https://maestrofin-production.up.railway.app`
   - Salve e aguarde 2 minutos

3. **Dependências instaladas**
   ```bash
   pip install -r requirements.txt
   ```

## Como Rodar o Teste

### 1. Execute o script
```bash
python test_pluggy_oauth.py
```

### 2. Siga as instruções na tela

O script vai guiá-lo por cada etapa:

**Passo 1: Criar Link Token**
- Digite um ID de usuário (qualquer texto, ex: `user-123`)

**Passo 2: Escolher o banco**
- O script lista bancos disponíveis com OAuth
- Digite o número correspondente ao banco que quer testar

**Passo 3: Criar conexão**
- Digite o CPF do titular da conta (apenas números)
- O script cria a conexão e gera a URL de OAuth

**Passo 4: Login no banco**
- O script abre automaticamente o navegador
- Faça login no banco normalmente
- Autorize o acesso quando solicitado
- O banco vai redirecionar para o callback (pode aparecer erro na página, é normal se o servidor não estiver rodando)

**Passo 5: Verificação automática**
- Pressione ENTER após completar o login
- O script fica consultando o status até ficar `HEALTHY`
- Pode levar até 2-3 minutos

**Passo 6: Dados bancários**
- O script mostra as contas e transações encontradas

## Exemplo de Saída

```
🚀 TESTE AUTOMÁTICO - FLUXO OAUTH PLUGGY
======================================================================

📝 Passo 1: Criando Link Token...
✅ Link Token criado: lk_abc123

📋 Passo 2: Listando bancos disponíveis com OAuth...
✅ 45 bancos encontrados com OAuth

Bancos disponíveis:
  1. Banco Inter (ID: 201)
  2. Nubank (ID: 202)
  ...

Escolha um banco (1-10): 1
✅ Selecionado: Banco Inter (ID: 201)

🔗 Passo 3: Criando Item (conexão OAuth)...
Digite o CPF do titular: 00000000191
✅ Item criado: it_456789
✅ Status inicial: WAITING_USER_INPUT

🌐 OAuth URL gerada:
   https://connect.pluggy.ai/oauth?state=...

🔐 Passo 4: Abrindo navegador para login no banco...
Deseja abrir o navegador agora? (s/n): s
⏳ Aguardando você completar o login no banco...
   Pressione ENTER depois de fazer login e autorizar ⏎

🔄 Passo 5: Verificando status do Item...
   Status: WAITING_USER_INPUT
   Status: UPDATING
   Status: HEALTHY

✅ Item conectado com sucesso! Status: HEALTHY

======================================================================
💰 Passo 6: Buscando dados bancários...
======================================================================

📊 Contas encontradas:
   • Conta Corrente - Tipo: CHECKING - Saldo: BRL 1234.56
   • Poupança - Tipo: SAVINGS - Saldo: BRL 500.00

📈 Últimas transações:
   • 2025-11-15 - Pagamento PIX - R$ -50.00
   • 2025-11-14 - Salário - R$ 5000.00

======================================================================
✅ TESTE CONCLUÍDO COM SUCESSO!
======================================================================
```

## Possíveis Erros

### ❌ "Variáveis de ambiente não configuradas"
- Crie o arquivo `.env` com as credenciais corretas

### ❌ "OAuth URL não foi retornada"
- Verifique se o `redirectUri` está cadastrado no Pluggy
- Confirme que o banco escolhido suporta OAuth

### ❌ Status fica em "WAITING_FOR_OAUTH_REDIRECT"
- O redirect não foi recebido
- Verifique se o domínio cadastrado no Pluggy está correto
- Confirme que você completou o login no banco

### ❌ "INVALID_CREDENTIALS"
- CPF ou credenciais do banco estão incorretos
- Tente novamente com dados válidos

### ⏰ "Timeout: Item não ficou saudável"
- Alguns bancos levam mais tempo
- Execute novamente o polling manualmente:
  ```bash
  python -c "from pluggy import PluggyClient; import os; pluggy = PluggyClient(os.getenv('PLUGGY_CLIENT_ID'), os.getenv('PLUGGY_CLIENT_SECRET')); print(pluggy.items.get('seu_item_id'))"
  ```

## Próximos Passos

Após confirmar que o teste funciona:

1. **Integre ao bot**
   - Use o código de `open_finance/pluggy_client.py`
   - Implemente handlers no Telegram para guiar o usuário

2. **Configure webhooks** (opcional)
   - No dashboard Pluggy: **Settings → Webhooks**
   - Adicione: `https://maestrofin-production.up.railway.app/pluggy/webhook`
   - Receba notificações automáticas quando dados forem atualizados

3. **Sincronização automática**
   - Configure jobs periódicos para atualizar transações
   - Use `pluggy.items.update(itemId)` para forçar sincronização
