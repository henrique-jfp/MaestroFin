# Fluxo OAuth Completo - Pluggy Open Finance

Este guia descreve o fluxo exato para conectar uma instituição via OAuth utilizando o `pluggy-sdk-python`. Ele cobre desde a criação do Link Token até o polling final do Item.

## 1. Criar Link Token

```python
link_token = pluggy.links.create({
    "clientUserId": str(user_id),
    "products": ["ACCOUNTS", "TRANSACTIONS"],
    "webhook": "https://meusite.com/pluggy/webhook"  # opcional
})
```

- Use um `clientUserId` único por usuário.
- Defina o `webhook` se quiser receber notificações.

## 2. Listar/Selecionar Instituição (Connector)

```python
connectors = pluggy.connectors.list(country="BR", oauth=True)
```

- Mostre apenas instituições com `oauth=True` para este fluxo.

## 3. Criar Item com redirect autorizado

```python
item = pluggy.items.create({
    "connectorId": connector_id,
    "linkTokenId": link_token["id"],
    "parameters": ConnectorParameters(cpf=cpf),
    "redirectUri": "https://meusite.com/pluggy/callback"
})
```

- `redirectUri` **precisa** estar cadastrado no dashboard Pluggy → *Settings → Redirect URIs*.
- Guarde `item['id']` e `item['status']`.

## 4. Redirecionar usuário

- O Pluggy vai retornar `item['nextAuthStep']['oauthRedirect']` ou `item['redirectUrl']`.
- Envie o usuário para este URL (inline button, deep link, etc.).

## 5. Usuário autoriza no banco

- O banco autentica (app/website) e chama `redirectUri` com `code` + `state`.

## 6. Callback `/pluggy/callback`

```python
@app.route("/pluggy/callback")
def pluggy_callback():
    code = request.args["code"]
    state = request.args["state"]
    pluggy.items.exchange_oauth_code(code=code, state=state)
    # opcional: retornar página amigável ao usuário
    return "Autorização recebida!", 200
```

- O `state` é o `itemId` (ou token gerado). Pluggy valida internamente.
- Após `exchange_oauth_code`, o item muda para `UPDATING`.

## 7. Polling do Item

```python
def wait_item_ready(item_id, timeout=300):
    end = time.time() + timeout
    last_status = None
    while time.time() < end:
        item = pluggy.items.get(item_id)
        status = item.get("status")
        if status != last_status:
            logger.info("Item %s status=%s detail=%s", item_id, status, item.get("statusDetail"))
            last_status = status
        if status in ("HEALTHY", "PARTIAL_SUCCESS"):
            return item
        if status in ("LOGIN_ERROR", "INVALID_CREDENTIALS", "ERROR", "SUSPENDED"):
            raise RuntimeError(f"Item falhou: {item.get('statusDetail')}")
        time.sleep(5)
    raise TimeoutError("Item não sincronizou a tempo")
```

## 8. Sincronização final

- Depois de `HEALTHY`, busque contas (`pluggy.accounts.list(item_id=item_id)`) e transações (`pluggy.transactions.list(item_id=item_id)`).

## Observações Cruciais

1. **Redirect URI**: precisa estar em `Settings → Redirect URIs` do dashboard.
2. **HTTPS obrigatório** (ou `http://localhost` para testes locais).
3. **Estado**: se quiser garantir, salve `state` antes e confirme na volta.
4. **Timeouts**: podem levar até 2-3 minutos dependendo do banco.
5. **Webhooks**: últil para receber `item.updated` sem polling constante.
