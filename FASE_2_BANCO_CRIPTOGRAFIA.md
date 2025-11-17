# 🔐 Fase 2: Integração com Banco de Dados + Criptografia

## ✅ O que foi implementado

### 1. **Criptografia de Tokens** (`open_finance/token_encryption.py`)
- Usa **Fernet** (symmetric encryption) da biblioteca `cryptography`
- Tokens criptografados antes de serem salvos no BD
- Descriptografiados automaticamente ao recuperar
- Chave armazenada em variável de ambiente: `TOKEN_ENCRYPTION_KEY`

```python
from open_finance.token_encryption import get_encryption

encryption = get_encryption()
encrypted = encryption.encrypt("token_do_banco")  # ✅ Salva no BD
decrypted = encryption.decrypt(encrypted)         # ✅ Recupera do BD
```

### 2. **Banco de Dados** (`models.py` - Nova tabela)
```sql
CREATE TABLE user_bank_tokens (
  id SERIAL PRIMARY KEY,
  id_usuario INT FOREIGN KEY,
  banco VARCHAR(20),              -- 'inter', 'itau', etc
  encrypted_token TEXT,            -- Token criptografado ⚠️ NUNCA plain text
  token_type VARCHAR(50),          -- 'isafe', 'itoken', 'bearer', etc
  conectado_em TIMESTAMP,
  ultimo_acesso TIMESTAMP,
  ativo BOOLEAN DEFAULT true
);
```

### 3. **Gerenciador de BD** (`open_finance/token_database.py`)

Funções principais:
- `save_token()` - Salva token criptografado
- `get_token()` - Recupera e decripta token
- `delete_token()` - Marca como inativo
- `has_active_token()` - Verifica se tem token ativo
- `get_all_tokens()` - Lista todos os bancos conectados

```python
from open_finance.token_database import TokenDatabaseManager
from database.database import SessionLocal

db = SessionLocal()
manager = TokenDatabaseManager(db)

# Salvar
manager.save_token(user_id=123, bank='inter', token='...', token_type='isafe')

# Recuperar
token_data = manager.get_token(user_id=123, bank='inter')
print(token_data)  # {'token': 'decriptografado', 'token_type': 'isafe', ...}

# Listar todos
tokens = manager.get_all_tokens(user_id=123)
```

### 4. **TokenAuthManager Atualizado** (`open_finance/token_auth.py`)

Agora suporta persistência:
```python
from open_finance.token_auth import TokenAuthManager
from database.database import SessionLocal

db = SessionLocal()
manager = TokenAuthManager(db_session=db)

# Valida e salva automaticamente no BD
auth_data = manager.authenticate('inter', '123456')
manager.store_token(user_id=123, bank='inter', auth_data=auth_data)

# Recupera (tenta BD primeiro, fallback memória)
token = manager.get_token(user_id=123, bank='inter')
```

### 5. **Handler Telegram** (`gerente_financeiro/token_auth_handler.py`)

Agora recebe DB session:
```python
from gerente_financeiro.token_auth_handler import TokenAuthHandler
from database.database import SessionLocal

handler = TokenAuthHandler(db_session=SessionLocal())
# Tokens automaticamente persistidos no BD quando usuário envia
```

## 🔄 Fluxo Completo (Com Dados Reais)

```
1. Usuário envia /conectar_token
   ↓
2. Seleciona banco (Inter, Itaú, etc)
   ↓
3. Handler recebe token via Telegram
   ↓
4. TokenAuthManager valida formato
   ↓
5. ✅ TokenEncryption criptografa
   ↓
6. ✅ TokenDatabaseManager salva em BD
   ↓
7. ✅ Bot responde "Conectado!"
   ↓
8. Bot reinicia
   ↓
9. ✅ Token recuperado do BD automaticamente
```

## 🔐 Segurança

### ✅ O que está protegido:
1. **Tokens NUNCA em plain text** - Sempre criptografados
2. **BD isolada** - Tokens separados em tabela dedicada
3. **Chave segura** - Armazenada em variável de ambiente (não em código)
4. **Sem backup em cache** - Memória limpa quando bot reinicia

### ⚠️ O que falta (Fase 3):
- [ ] Rotação de tokens (expiração automática)
- [ ] Auditoria de acessos (log quem acessou quando)
- [ ] Two-factor authentication (2FA)
- [ ] Token refresh automático

## 🚀 Como usar em produção

### 1. Gerar chave de criptografia:
```python
from open_finance.token_encryption import TokenEncryption
key = TokenEncryption.generate_new_key()
print(key)  # gAAAAABl... (copiar)
```

### 2. Adicionar ao .env (Render):
```env
TOKEN_ENCRYPTION_KEY=gAAAAABl... (copiar da chave gerada)
```

### 3. Bot criará tabela automaticamente:
```
✅ Tabela user_bank_tokens criada no primeiro boot
```

### 4. Testar com token real:
```
/conectar_token
→ Selecionar banco
→ Enviar token (6 dígitos ou bearer)
→ Verificar em DB: SELECT * FROM user_bank_tokens WHERE id_usuario = X
```

## 📊 Próximos Passos (Fase 3)

### API Calls Reais
```python
# Usar token do BD para fazer chamada real ao banco
token_data = manager.get_token(user_id=123, bank='inter')
token = token_data['token']  # Descriptografado automaticamente

# Fazer chamada à API do Inter com token
response = requests.get(
    'https://api.inter.com/transacoes',
    headers={'Authorization': f'Bearer {token}'}
)
```

### Sincronização Automática
```python
# Agenda tarefa para sync diário
from gerente_financeiro.services import sync_bank_transactions

# A cada 6 horas
sync_bank_transactions(user_id=123)
```

## ✅ Checklist de Verificação

- [x] Tabela `user_bank_tokens` criada
- [x] Criptografia Fernet implementada
- [x] TokenDatabaseManager funcional
- [x] TokenAuthManager integrado com BD
- [x] Handler passando DB session
- [x] Bot.py importando SessionLocal
- [x] Requirements atualizado com `cryptography`
- [x] Commit e push em restore-v1.0.0
- [ ] Testar em produção (Render)
- [ ] Gerar e configurar chave encryption no Render
- [ ] Testar com token real
- [ ] Verificar dados em PostgreSQL

## 🎯 Status

**Commit**: `92524c0`
**Branch**: `restore-v1.0.0`
**Deploy**: Aguardando em Render (auto-redeploy em andamento)

---

**Próxima fase**: Implementar API calls reais aos bancos
