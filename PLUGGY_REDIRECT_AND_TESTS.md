# Redirect URI & Checklist de Testes Pluggy OAuth

## 1. Configurando o Redirect URI

1. Acesse o dashboard da Pluggy → **Settings → Redirect URIs**.
2. Adicione cada URL que possa ser usada no fluxo:
   - Produção: `https://meusite.com/pluggy/callback`
   - Staging: `https://staging.meusite.com/pluggy/callback`
   - Local: `http://localhost:8000/pluggy/callback`
3. Salve e aguarde alguns segundos (pode levar até 2 minutos para propagar).
4. Use exatamente a mesma URL ao criar o Item (`redirectUri`).
5. Verifique se o domínio usa HTTPS válido (exceto `localhost`).

## 2. Checklist de Testes

### Antes do teste
- [ ] Variáveis de ambiente configuradas (`PLUGGY_CLIENT_ID`, `PLUGGY_CLIENT_SECRET`, `PLUGGY_REDIRECT_URI`).
- [ ] SDK atualizado: `pip install -U pluggy-sdk-python`.
- [ ] `redirectUri` cadastrado no dashboard.

### Fluxo OAuth
1. **Criar Link Token**
   - [ ] `POST /pluggy/link-token` retorna `id`.
   - [ ] Response contém `redirectUri` correto.

2. **Criar Item**
   - [ ] `POST /pluggy/connect` retorna `itemId` e `oauthUrl`.
   - [ ] Dashboard mostra item em `waiting_for_user_input`.

3. **Abrir OAuth**
   - [ ] Usuário visita `oauthUrl`.
   - [ ] Banco apresenta tela de login.

4. **Callback**
   - [ ] `GET /pluggy/callback?code=...&state=...` é chamado.
   - [ ] Logs mostram `Received OAuth redirect`.
   - [ ] `exchange_oauth_code` não lança erro.

5. **Polling**
   - [ ] Logs mostram transição `waiting_for_oauth_redirect → updating → healthy`.
   - [ ] Response final `OAuth completed!`.

6. **Verificação Final**
   - [ ] Dashboard da Pluggy mostra `OAuth redirect received`.
   - [ ] `GET /pluggy/items/<itemId>` retorna `status=HEALTHY`.
   - [ ] `pluggy.accounts.list(itemId=itemId)` retorna contas.

### Em caso de falha
- [ ] Se status ficar em `waiting_for_oauth_redirect`, verificar:
  - Campo `redirectUri` bate com o cadastrado?
  - Callback recebeu `code/state`?
  - Firewall bloqueando?
- [ ] Se status virar `invalid_credentials`, revisar credenciais do banco.
- [ ] Se timeout > 5 min, abrir ticket com Pluggy incluindo `itemId` e logs.
