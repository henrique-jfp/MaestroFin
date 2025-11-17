# 🗄️ Guia de Integração - Token Authentication com Banco de Dados

## 📋 Objetivo

Este documento descreve como migrar o armazenamento de tokens de **in-memory** para **PostgreSQL com criptografia**.

---

## 🔄 Fases de Implementação

### Phase 1 (✅ COMPLETO)
- Validação de tokens
- Storage em memória
- Fluxo Telegram
- Instruções por banco

### Phase 2 (🔜 PRÓXIMA)
- Tabela BD para tokens
- Criptografia de tokens
- Migração de dados
- Testes

---

## 📊 Schema do Banco de Dados

### Tabela: `user_bank_tokens`

```sql
CREATE TABLE user_bank_tokens (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    bank VARCHAR(50) NOT NULL,
    
    -- Token criptografado
    encrypted_token TEXT NOT NULL,
    
    -- Metadados
    token_type VARCHAR(50),  -- 'cpf_token', 'bearer_token', 'jwt_token', etc
    cpf_masked VARCHAR(11),  -- Apenas CPF parcial para Inter (123***89)
    
    -- Datas
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP,
    expires_at TIMESTAMP,  -- Para tokens com expiração
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    validation_status VARCHAR(50),  -- 'valid', 'expired', 'revoked'
    
    -- Auditoria
    created_from_ip VARCHAR(45),
    user_agent TEXT,
    
    UNIQUE(user_id, bank),
    FOREIGN KEY(user_id) REFERENCES users(telegram_id) ON DELETE CASCADE
);

-- Índices
CREATE INDEX idx_user_bank_tokens_user_id ON user_bank_tokens(user_id);
CREATE INDEX idx_user_bank_tokens_bank ON user_bank_tokens(bank);
CREATE INDEX idx_user_bank_tokens_active ON user_bank_tokens(is_active, user_id);
CREATE INDEX idx_user_bank_tokens_expires ON user_bank_tokens(expires_at);
```

### Tabela: `token_audit_log`

```sql
CREATE TABLE token_audit_log (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    bank VARCHAR(50),
    action VARCHAR(50),  -- 'created', 'used', 'refreshed', 'deleted', 'expired'
    details TEXT,  -- JSON com detalhes
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY(user_id) REFERENCES users(telegram_id) ON DELETE CASCADE
);

CREATE INDEX idx_token_audit_log_user_id ON token_audit_log(user_id);
CREATE INDEX idx_token_audit_log_action ON token_audit_log(action);
```

---

## 🔐 Criptografia de Tokens

### Variáveis de Ambiente

```bash
# .env
TOKEN_ENCRYPTION_KEY=gerada-com-secrets.token_urlsafe(32)
TOKEN_ENCRYPTION_SALT=gerada-com-os.urandom(16)
```

### Implementação

```python
# open_finance/token_crypto.py

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
import os
import base64

class TokenCrypto:
    """Criptografia de tokens"""
    
    @staticmethod
    def generate_key() -> str:
        """Gera chave criptográfica"""
        key = Fernet.generate_key()
        return key.decode()
    
    @staticmethod
    def get_cipher():
        """Retorna cipher para usar"""
        key_env = os.getenv('TOKEN_ENCRYPTION_KEY')
        if not key_env:
            raise ValueError("TOKEN_ENCRYPTION_KEY não configurada")
        return Fernet(key_env.encode())
    
    @staticmethod
    def encrypt_token(token: str) -> str:
        """Criptografa token"""
        cipher = TokenCrypto.get_cipher()
        encrypted = cipher.encrypt(token.encode())
        return encrypted.decode()
    
    @staticmethod
    def decrypt_token(encrypted_token: str) -> str:
        """Descriptografa token"""
        cipher = TokenCrypto.get_cipher()
        decrypted = cipher.decrypt(encrypted_token.encode())
        return decrypted.decode()

# Testes
key = TokenCrypto.generate_key()
token = "12345678901:abc123def456"
encrypted = TokenCrypto.encrypt_token(token)
decrypted = TokenCrypto.decrypt_token(encrypted)
assert token == decrypted
```

---

## 🗄️ Migração do TokenAuthManager

### Antes (In-Memory)

```python
class TokenAuthManager:
    def __init__(self):
        self.tokens = {}  # Em memória
    
    def store_token(self, user_id, bank, auth_data):
        self.tokens[user_id][bank] = auth_data
```

### Depois (Com BD)

```python
from database.database import Database
from open_finance.token_crypto import TokenCrypto

class TokenAuthManager:
    def __init__(self, db: Database = None):
        self.db = db or Database()
    
    def store_token(self, user_id: int, bank: str, auth_data: Dict) -> None:
        """Armazena token em BD com criptografia"""
        
        # Preparar dados
        token_to_encrypt = auth_data['token']
        encrypted_token = TokenCrypto.encrypt_token(token_to_encrypt)
        
        # CPF parcial (se aplicável)
        cpf_masked = None
        if 'cpf' in auth_data:
            cpf = auth_data['cpf']
            cpf_masked = f"{cpf[:3]}***{cpf[-2:]}"
        
        # Inserir/Atualizar em BD
        query = """
            INSERT INTO user_bank_tokens 
            (user_id, bank, encrypted_token, token_type, cpf_masked, is_active)
            VALUES (%s, %s, %s, %s, %s, TRUE)
            ON CONFLICT (user_id, bank) DO UPDATE SET
                encrypted_token = %s,
                last_used_at = CURRENT_TIMESTAMP
        """
        
        self.db.execute(
            query,
            (
                user_id,
                bank,
                encrypted_token,
                auth_data.get('type', 'bearer_token'),
                cpf_masked,
                encrypted_token,  # Para UPDATE
            )
        )
        
        # Log auditoria
        self._audit_log(user_id, bank, 'created', {'type': auth_data.get('type')})
    
    def get_token(self, user_id: int, bank: str) -> Optional[Dict]:
        """Recupera token do BD (descriptografado)"""
        
        query = """
            SELECT encrypted_token, token_type, cpf_masked, created_at
            FROM user_bank_tokens
            WHERE user_id = %s AND bank = %s AND is_active = TRUE
        """
        
        result = self.db.fetch_one(query, (user_id, bank))
        
        if not result:
            return None
        
        # Descriptografar
        decrypted_token = TokenCrypto.decrypt_token(result['encrypted_token'])
        
        # Log auditoria
        self._audit_log(user_id, bank, 'used')
        
        return {
            'token': decrypted_token,
            'type': result['token_type'],
            'cpf_masked': result['cpf_masked'],
            'created_at': result['created_at'],
        }
    
    def list_tokens(self, user_id: int) -> Dict:
        """Lista todos os tokens do usuário"""
        
        query = """
            SELECT bank, token_type, cpf_masked, created_at, last_used_at
            FROM user_bank_tokens
            WHERE user_id = %s AND is_active = TRUE
            ORDER BY created_at DESC
        """
        
        results = self.db.fetch_all(query, (user_id,))
        
        tokens = {}
        for row in results:
            tokens[row['bank']] = {
                'type': row['token_type'],
                'cpf_masked': row['cpf_masked'],
                'created_at': row['created_at'],
                'last_used_at': row['last_used_at'],
            }
        
        return tokens
    
    def delete_token(self, user_id: int, bank: str) -> bool:
        """Remove token (soft delete)"""
        
        query = """
            UPDATE user_bank_tokens
            SET is_active = FALSE, validation_status = 'revoked'
            WHERE user_id = %s AND bank = %s
            RETURNING id
        """
        
        result = self.db.execute(query, (user_id, bank))
        
        if result:
            self._audit_log(user_id, bank, 'deleted')
            return True
        
        return False
    
    def _audit_log(self, user_id: int, bank: str, action: str, details: Dict = None):
        """Registra ação para auditoria"""
        
        query = """
            INSERT INTO token_audit_log (user_id, bank, action, details)
            VALUES (%s, %s, %s, %s)
        """
        
        import json
        self.db.execute(
            query,
            (user_id, bank, action, json.dumps(details or {}))
        )
```

---

## 🔄 Processo de Migração

### Step 1: Criar Tabelas

```python
# migrations/001_create_token_tables.py

def up(db):
    """Cria tabelas"""
    db.execute("""
        CREATE TABLE user_bank_tokens (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            bank VARCHAR(50) NOT NULL,
            encrypted_token TEXT NOT NULL,
            token_type VARCHAR(50),
            cpf_masked VARCHAR(11),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_used_at TIMESTAMP,
            expires_at TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE,
            validation_status VARCHAR(50),
            created_from_ip VARCHAR(45),
            user_agent TEXT,
            UNIQUE(user_id, bank),
            FOREIGN KEY(user_id) REFERENCES users(telegram_id) ON DELETE CASCADE
        )
    """)
    
    db.execute("""
        CREATE TABLE token_audit_log (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            bank VARCHAR(50),
            action VARCHAR(50),
            details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(telegram_id) ON DELETE CASCADE
        )
    """)
    
    # Índices
    db.execute("""
        CREATE INDEX idx_user_bank_tokens_user_id ON user_bank_tokens(user_id)
    """)

def down(db):
    """Desfaz migração"""
    db.execute("DROP TABLE token_audit_log")
    db.execute("DROP TABLE user_bank_tokens")
```

### Step 2: Atualizar TokenAuthManager

```python
# open_finance/token_auth.py

from database.database import Database
from open_finance.token_crypto import TokenCrypto

class TokenAuthManager:
    def __init__(self):
        self.db = Database()
        self.tokens_cache = {}  # Cache em memória para performance
    
    # ... implementação com BD (como descrito acima)
```

### Step 3: Testes

```python
# testes/test_token_auth_db.py

def test_store_and_retrieve():
    manager = TokenAuthManager()
    
    # Armazenar
    manager.store_token(
        user_id=123456789,
        bank='inter',
        auth_data={
            'bank': 'inter',
            'cpf': '12345678901',
            'token': 'abc123def456ghi789',
            'type': 'cpf_token'
        }
    )
    
    # Recuperar
    stored = manager.get_token(123456789, 'inter')
    
    assert stored['token'] == 'abc123def456ghi789'
    assert stored['cpf_masked'] == '123***01'
```

---

## 🔄 Fallback para In-Memory

Se BD não estiver disponível, usar in-memory como fallback:

```python
class TokenAuthManager:
    def __init__(self, use_db: bool = None):
        if use_db is None:
            use_db = os.getenv('DATABASE_URL') is not None
        
        self.use_db = use_db
        self.in_memory_tokens = {}
        
        if self.use_db:
            self.db = Database()
        else:
            logger.warning("⚠️ TokenAuthManager em modo IN-MEMORY")
    
    def store_token(self, user_id, bank, auth_data):
        if self.use_db:
            # Lógica BD
            pass
        else:
            # In-memory
            if user_id not in self.in_memory_tokens:
                self.in_memory_tokens[user_id] = {}
            self.in_memory_tokens[user_id][bank] = auth_data
```

---

## 📊 Auditoria

### Consultas Úteis

```sql
-- Ver tokens ativos de um usuário
SELECT bank, token_type, cpf_masked, created_at, last_used_at
FROM user_bank_tokens
WHERE user_id = 123456789 AND is_active = TRUE;

-- Ver histórico de ações
SELECT user_id, bank, action, details, created_at
FROM token_audit_log
WHERE user_id = 123456789
ORDER BY created_at DESC
LIMIT 20;

-- Tokens expirados
SELECT user_id, bank, expires_at
FROM user_bank_tokens
WHERE expires_at < CURRENT_TIMESTAMP AND is_active = TRUE;

-- Tokens não usados há X dias
SELECT user_id, bank, created_at, last_used_at
FROM user_bank_tokens
WHERE last_used_at < CURRENT_TIMESTAMP - INTERVAL '30 days';
```

---

## 🛡️ Segurança

### Checklist

- [ ] Chave criptográfica em variável de ambiente
- [ ] Nunca logar tokens em texto plano
- [ ] Rotação de chaves implementada
- [ ] Acesso BD via conexão segura (SSL)
- [ ] Auditoria de todas as operações
- [ ] Backup criptografado
- [ ] Rate limiting em operações
- [ ] Validação de entrada

---

## 📈 Performance

### Otimizações

```python
# Cache em memória
class TokenAuthManager:
    def __init__(self):
        self.cache = {}  # {user_id: {bank: token_data}}
        self.cache_ttl = 3600  # 1 hora
    
    def get_token(self, user_id, bank):
        # Verificar cache
        if self._is_cached(user_id, bank):
            return self.cache[(user_id, bank)]
        
        # BD se não em cache
        token = self.db.get_token(user_id, bank)
        
        # Armazenar em cache
        self._cache_set(user_id, bank, token)
        
        return token
    
    def _is_cached(self, user_id, bank):
        key = (user_id, bank)
        return key in self.cache
```

---

## 🚀 Timeline

- **Semana 1**: Criar tabelas e migração
- **Semana 2**: Implementar criptografia
- **Semana 3**: Testes e validações
- **Semana 4**: Deploy em produção

---

## 📝 Checklist Final

- [ ] Schema BD criado
- [ ] Migrações implementadas
- [ ] Criptografia funciona
- [ ] TokenAuthManager usa BD
- [ ] Auditoria log implementada
- [ ] Testes passam
- [ ] Fallback in-memory funciona
- [ ] Deploy testado
- [ ] Documentação atualizada
- [ ] Backups configurados

---

**Status**: 🔜 Próxima fase  
**Prioridade**: Alta  
**Estimativa**: 1 semana
