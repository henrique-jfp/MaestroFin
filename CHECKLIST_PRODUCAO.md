# ✅ Checklist - O que fazer em Produção

## 🚀 IMEDIATO (Hoje/Amanhã)

- [ ] **Render Dashboard**
  - [ ] Abrir https://dashboard.render.com/
  - [ ] Selecionar projeto MaestroFin
  - [ ] Ir em "Environment"
  
- [ ] **Gerar Chave de Criptografia** (local)
  ```bash
  python3 -c "from open_finance.token_encryption import TokenEncryption; print(TokenEncryption.generate_new_key())"
  ```
  - [ ] Copiar saída (começa com `gAAAAABl...`)
  
- [ ] **Adicionar ao Render**
  - [ ] Click "+ Add Environment Variable"
  - [ ] Key: `TOKEN_ENCRYPTION_KEY`
  - [ ] Value: `gAAAAABl...` (colar)
  - [ ] Click "Save Changes"
  - [ ] Render vai fazer redeploy automaticamente (2-3 min)
  
- [ ] **Verificar Redeploy**
  - [ ] Refresh Render Dashboard
  - [ ] Verificar logs: "✅ Deploy successful"
  
- [ ] **Testar no Telegram**
  - [ ] Enviar `/conectar_token` no bot
  - [ ] Selecionar um banco (Inter, Itaú, etc)
  - [ ] Enviar token real (6 dígitos ou bearer)
  - [ ] Verificar: ✅ Token de [BANCO] Validado!
  
- [ ] **Verificar Banco de Dados**
  - [ ] PostgreSQL Render Console
  - [ ] Executar:
    ```sql
    SELECT COUNT(*) FROM user_bank_tokens;
    ```
  - [ ] Deve retornar: 1 (ou mais se testou múltiplas vezes)
  
- [ ] **Validar Criptografia**
  - [ ] Executar:
    ```sql
    SELECT encrypted_token FROM user_bank_tokens LIMIT 1;
    ```
  - [ ] Deve mostrar: `gAAAAABl...` (criptografado)
  - [ ] NUNCA: token em plain text como `123456`

---

## 🧪 TESTES (Próximos dias)

- [ ] **Teste 1: Múltiplos Tokens**
  - [ ] Conectar Inter → Validar
  - [ ] Conectar Itaú → Validar
  - [ ] Conectar Bradesco → Validar
  - [ ] Listar: `/listar_bancos` (comando a criar)
  
- [ ] **Teste 2: Persistência**
  - [ ] Conectar token
  - [ ] Reiniciar bot: `Render → Manual Restart`
  - [ ] Verificar token foi recuperado
  - [ ] Sem precisar reconectar
  
- [ ] **Teste 3: Segurança**
  - [ ] Verificar logs não mostram token plain text
  - [ ] Verificar BD só tem tokens criptografados
  - [ ] Verificar arquivo de logs não tem tokens
  
- [ ] **Teste 4: Erro Handling**
  - [ ] Enviar token inválido
  - [ ] Enviar token muito curto
  - [ ] Enviar caracteres especiais
  - [ ] Verificar mensagens de erro claras

---

## 📝 PRÓXIMAS FASES (Próximas semanas)

### Fase 3: API Calls Reais
- [ ] Criar `open_finance/bank_api_client.py`
- [ ] Implementar endpoints reais:
  - [ ] Inter API
  - [ ] Itaú API
  - [ ] Bradesco API
  - [ ] Nubank API
  - [ ] Caixa API
  - [ ] Santander API

### Fase 4: Sincronização Automática
- [ ] Criar agendamento: `jobs.py`
- [ ] Schedule sync a cada 6 horas
- [ ] Notificar usuário de transações
- [ ] Atualizar saldos automáticos

### Fase 5: Integração com MaestroFin
- [ ] Mapear transações → Categorias
- [ ] Salvar como Lancamentos
- [ ] Atualizar metas automáticas
- [ ] Dashboard com dados reais

---

## 📊 Métricas de Sucesso

✅ **Considerado sucesso quando:**
- Token salvo no BD com sucesso
- Token descriptografado corretamente
- Bot pode recuperar token após restart
- Mensagens de erro apropriadas
- Logs não mostram token em plain text
- Usuário consegue conectar e ver status

---

## 🆘 Troubleshooting

### Problema: "❌ TOKEN_ENCRYPTION_KEY não definida"
**Solução:**
1. Gerar chave: `python3 -c "from open_finance.token_encryption import TokenEncryption; print(TokenEncryption.generate_new_key())"`
2. Adicionar ao Render Environment Variables
3. Render redeploy

### Problema: Erro ao salvar token no BD
**Solução:**
1. Verificar `DATABASE_URL` está correta em Render
2. Verificar tabela `user_bank_tokens` existe: `\dt user_bank_tokens`
3. Se não existe: `python manage.py migrate`

### Problema: Token aparece em plain text no BD
**Solução:**
⚠️ **CRÍTICO** - Isso nunca deveria acontecer
1. Verificar `TOKEN_ENCRYPTION_KEY` está configurada
2. Verificar `token_encryption.py` está sendo usado
3. Fazer rollback se necessário

### Problema: Bot não inicia após adicionar variável
**Solução:**
1. Verificar logs do Render
2. Procurar por erros relacionados a `cryptography`
3. Verificar `requirements.txt` tem `cryptography==43.0.0`
4. Se não: adicionar e fazer push

---

## 📞 Referências

- [Render Docs](https://render.com/docs)
- [Cryptography.io](https://cryptography.io/)
- [PostgreSQL Docs](https://www.postgresql.org/docs/)

---

**Última atualização**: 17/11/2025
**Commit**: 3297797
**Branch**: restore-v1.0.0
