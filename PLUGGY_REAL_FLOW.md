# Análise do Fluxo Real do Pluggy

## O Problema Atual

O bot mostra mensagem genérica sem link de autorização:
```
⚠️ Confirmação Bancária Necessária
O banco solicitou uma confirmação adicional.
```

Mas deveria mostrar um botão com link para autorizar no banco.

## Como Pluggy Realmente Funciona

Baseado em análise da arquitetura:

### 1. **Fluxo Tradicional (Desktop Web)**
- Usuário cria item via API com CPF
- Pluggy retorna `redirectUrl` 
- Usuário é enviado para Pluggy web interface
- Pluggy redireciona para app do banco
- Usuário faz login e autoriza
- Pluggy synchroniza dados

### 2. **Fluxo Telegram (Mobile)**
Aqui está o problema: **Telegram não suporta redirecionamentos 100% nativos**

Opções disponíveis no Telegram:
1. **InlineKeyboardButton com `url=`** ✅ Abre link em browser
2. **InlineKeyboardButton com `callback_query`** - Retorna ao bot
3. **Message com link** - Usuário copia e abre

## Solução Proposta

### Passo 1: Verificar se Pluggy Retorna redirectUrl
Usar `investigate_pluggy.py` com credenciais REAIS para ver resposta

### Passo 2: Caso Pluggy Retorne redirectUrl
Colocar como botão inline no Telegram:
```python
InlineKeyboardButton("🔐 Autorizar no Banco", url=redirect_url)
```

### Passo 3: Caso Pluggy NÃO Retorne (ou use deepLink)
Construir URL manualmente:
```
https://dashboard.pluggy.ai/items/{item_id}/authentication?apiKey={api_key}
```

### Passo 4: Polling para Sincronização
Depois que usuário clica no botão:
1. Pluggy aguarda autenticação (5-10 minutos)
2. Bot faz polling de `get_item()` a cada 3 segundos
3. Quando `status` muda para `CONNECTED`, baixa dados
4. Avisa ao usuário ✅

## Hipóteses

**H1**: Pluggy retorna `redirectUrl` e código está correto
- Evidência: Código procura por `redirectUrl` e `url`
- Ação: Verificar se campo está vindo vazio

**H2**: Pluggy não retorna nada no `create_item()`
- Evidência: Status retornado como `WAITING_USER_INPUT`
- Ação: Construir URL manualmente com item_id

**H3**: Código foi deployard mas container não foi reiniciado
- Evidência: "não mudou nada..." do usuário
- Ação: Forçar reinicialização no Render

## Próximos Passos

1. ✅ Executar `investigate_pluggy.py` com CPF real
2. ✅ Verificar resposta JSON completa do Pluggy
3. ✅ Se `redirectUrl` vazio: construir URL manualmente
4. ✅ Se `redirectUrl` cheio: verificar Render deployment
5. ✅ Teste end-to-end com usuário real
