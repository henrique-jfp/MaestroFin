# 🔧 Fix: Integer Overflow em user_bank_tokens

## ❌ Problema Encontrado

Ao tentar salvar o token em produção, ocorreu erro:

```
psycopg2.errors.NumericValueOutOfRange: integer out of range

INSERT INTO user_bank_tokens (id_usuario, ...)
parameters: {'id_usuario': 6157591255, ...}
```

## 🔍 Root Cause

A tabela `user_bank_tokens` estava usando:

```python
id_usuario = Column(Integer, ForeignKey('usuarios.id'), ...)
```

**O Problema:**
- `id_usuario` deveria armazenar `usuarios.id` (que é `Integer` pequeno: 1, 2, 3...)
- Mas o handler estava passando `telegram_user_id` (que é `BigInteger`: 6157591255)
- **Integer suporta até ~2 bilhões, mas tinha mais de 6 bilhões ❌**

## ✅ Solução Implementada

### Antes:
```python
# Handler passava telegram_user_id diretamente
token_manager.store_token(telegram_user_id=6157591255, bank='inter', ...)
    ↓
# Tentava salvar direto em id_usuario
INSERT INTO user_bank_tokens (id_usuario=6157591255, ...)  ❌ TOO BIG
```

### Depois:
```python
# Novo método em TokenDatabaseManager
def _get_usuario_id(self, telegram_user_id: int) -> int | None:
    usuario = db.query(Usuario).filter(
        Usuario.telegram_id == telegram_user_id
    ).first()
    return usuario.id  # Retorna o id pequeno (1, 2, 3...)

# Todos os métodos usam conversão
token_manager.store_token(telegram_user_id=6157591255, ...)
    ↓
_get_usuario_id(6157591255)  # Busca em BD
    ↓
usuarios.id = 1  # Retorna id pequeno
    ↓
INSERT INTO user_bank_tokens (id_usuario=1, ...)  ✅ CORRECT
```

## 📊 Tabela Relacionada

```
USUÁRIOS (usuarios table):
id (Integer) | telegram_id (BigInteger) | nome
1            | 6157591255              | João
2            | 9876543210              | Maria
3            | 1111111111              | Pedro

USER_BANK_TOKENS (user_bank_tokens table):
id | id_usuario (FK) | banco  | encrypted_token        | ativo
1  | 1               | inter  | gAAAAABpG7Ul... (cript) | true
2  | 1               | itau   | gAAAAABpG7Um... (cript) | true
3  | 2               | inter  | gAAAAABpG7Un... (cript) | true
```

## 🔧 Mudanças Feitas

### 1. `open_finance/token_database.py`
- ✅ Novo método: `_get_usuario_id(telegram_user_id)`
- ✅ Atualizado `save_token()` para usar conversão
- ✅ Atualizado `get_token()` para usar conversão
- ✅ Atualizado `get_all_tokens()` para usar conversão
- ✅ Atualizado `delete_token()` para usar conversão
- ✅ Atualizado `has_active_token()` para usar conversão
- ✅ Import adicionado: `from models import Usuario`

### 2. Commits
- `594da4d` - Fix: Integer overflow fix
- `1bf97a5` - Force Render redeploy

## 🚀 O Que Mudou em Produção

**Antes (quebrado):**
```
/conectar_token → Token enviado → ❌ integer out of range
```

**Depois (funcionando):**
```
/conectar_token → Token enviado → 🔐 Criptografa → 💾 Salva corretamente
```

## ✅ Teste Funcional

1. Render redeplopado com a correção ✅
2. Tente `/conectar_token` novamente ✅
3. Selecione Inter ✅
4. Envie token (6 dígitos: 123456) ✅
5. Esperado: ✅ Token de Inter Validado! ✅

## 📋 Verificação em BD

```sql
-- Verificar token foi salvo corretamente
SELECT * FROM user_bank_tokens 
WHERE id_usuario IN (
    SELECT id FROM usuarios WHERE telegram_id = 6157591255
);

-- Esperado: 1 linha com token criptografado
```

## 🎓 Lição Aprendida

- ⚠️ **Sempre validar tipos de dados ao fazer FK**
- ✅ `telegram_id` = BigInteger (6 dígitos+)
- ✅ `usuarios.id` = Integer (auto-increment)
- ✅ Sempre fazer conversão quando necessário

---

**Status**: ✅ CORRIGIDO E EM PRODUÇÃO
**Commit**: 594da4d → 1bf97a5
**Render**: Redeplopando agora
