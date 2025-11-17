"""
🧪 Exemplo de Uso - Token Authentication

Demonstra como usar o novo sistema de autenticação por token
"""

# ======== EXEMPLO 1: Validação de Token (Sem Telegram) ========

from open_finance.token_auth import token_manager

# Testar validação Inter
try:
    auth_data = token_manager.authenticate('inter', '12345678901:abc123def456ghi789')
    print(f"✅ Inter token válido: {auth_data}")
except ValueError as e:
    print(f"❌ Erro: {e}")


# ======== EXEMPLO 2: Armazenar Token ========

user_id = 123456789
bank = 'inter'

# Após validação bem-sucedida
auth_data = token_manager.authenticate('inter', '12345678901:abc123def456ghi789')
token_manager.store_token(user_id, bank, auth_data)

# Recuperar token depois
stored = token_manager.get_token(user_id, 'inter')
print(f"💾 Token armazenado: {stored}")


# ======== EXEMPLO 3: Fluxo Completo no Telegram ========
"""
Quando um usuário usar /conectar_token:

1. Bot exibe menu:
   🔑 Conectar com Token de Segurança
   
   Este método é mais simples que Open Finance!
   
   Como funciona:
   1️⃣ Você gera um token no app/site do seu banco
   2️⃣ Cola o token aqui
   3️⃣ Pronto! Conectado instantaneamente
   
   [🏦 Inter] [🏦 Itaú] [🏦 Bradesco] [🏦 Nubank] [🏦 Caixa] [🏦 Santander]
   [❌ Cancelar]

2. Usuário clica em "Inter"

3. Bot mostra instruções:
   🔐 Inter Selecionado
   
   Como gerar o token no Inter:
   1️⃣ Acesse: https://eb.bancointer.com.br/
   2️⃣ Vá em 'Configurações' → 'API'
   3️⃣ Clique em 'Gerar novo token'
   4️⃣ Copie no formato: CPF:token
   
   Exemplo: 12345678901:abc123def456...
   
   Cole o token abaixo (será removido da conversa por segurança):

4. Usuário envia: 12345678901:abc123def456ghi789

5. Bot valida e responde:
   ✅ Token de Inter Validado!
   
   🔐 Conexão segura estabelecida
   📱 Status: Conectado
   💳 Banco: Inter
   
   Agora você pode:
   • /minhas_contas - Ver contas conectadas
   • /extrato - Ver transações
   • /saldo - Ver saldo consolidado
   
   Token será usado apenas para sincronizar dados do seu banco.
"""


# ======== EXEMPLO 4: Validações Específicas ========

# Token Inter
valid_inter = token_manager.validate_token('inter', '12345678901:abc123def456ghi')
print(f"Inter válido? {valid_inter}")

# Token Itaú
valid_itau = token_manager.validate_token('itau', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...')
print(f"Itaú válido? {valid_itau}")

# Token Bradesco
valid_bradesco = token_manager.validate_token('bradesco', 'abc123def456ghi789jklmno')
print(f"Bradesco válido? {valid_bradesco}")

# Token Nubank (JWT)
valid_nubank = token_manager.validate_token(
    'nubank',
    'eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwiZXhwIjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c'
)
print(f"Nubank válido? {valid_nubank}")

# Token Caixa
valid_caixa = token_manager.validate_token('caixa', 'abc-123-def-456-ghi-789')
print(f"Caixa válido? {valid_caixa}")

# Token Santander
valid_santander = token_manager.validate_token('santander', 'abc_123_def-456_ghi.789')
print(f"Santander válido? {valid_santander}")


# ======== EXEMPLO 5: Listar Tokens do Usuário ========

tokens = token_manager.list_tokens(user_id)
print(f"Tokens do usuário {user_id}: {tokens}")


# ======== EXEMPLO 6: Deletar Token ========

deleted = token_manager.delete_token(user_id, 'inter')
print(f"Token deletado? {deleted}")


# ======== EXEMPLO 7: Tratamento de Erros ========

# Erro: Banco não suportado
try:
    token_manager.authenticate('banco_invalido', 'token123')
except ValueError as e:
    print(f"❌ {e}")
    # Saída: ❌ Banco 'banco_invalido' não suportado para autenticação por token

# Erro: Token Inter sem CPF
try:
    token_manager.authenticate('inter', 'token_sem_cpf')
except ValueError as e:
    print(f"❌ {e}")
    # Saída: ❌ Token Inter deve estar no formato: CPF:token

# Erro: CPF com menos de 11 dígitos
try:
    token_manager.authenticate('inter', '123456789:token123')
except ValueError as e:
    print(f"❌ {e}")
    # Saída: ❌ CPF inválido

# Erro: Token muito curto
try:
    token_manager.authenticate('itau', 'abc123')
except ValueError as e:
    print(f"❌ {e}")
    # Saída: ❌ Token Itaú muito curto


# ======== EXEMPLO 8: Dados Armazenados ========

"""
Cada token armazenado contém:

Para Inter:
{
    'bank': 'inter',
    'cpf': '12345678901',  # CPF sem formatação
    'token': 'abc123def456...',
    'validated_at': '2024-01-15T10:30:45.123456'
}

Para Itaú:
{
    'bank': 'itau',
    'token': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...',
    'validated_at': '2024-01-15T10:30:45.123456'
}

Para Nubank (JWT):
{
    'bank': 'nubank',
    'token': 'eyJhbGciOiJIUzI1NiJ9...',
    'validated_at': '2024-01-15T10:30:45.123456'
}
"""


# ======== EXEMPLO 9: Próximas Integrações ========

"""
Futuros uso do token armazenado:

from gerente_financeiro.bank_connector import BankConnector

# Recuperar token do usuário
token_data = token_manager.get_token(user_id, 'inter')

# Usar com conector de banco
connector = BankConnector(bank='inter')
accounts = connector.get_accounts(token=token_data['token'])
transactions = connector.get_transactions(token=token_data['token'])

# Sincronizar com BD
for account in accounts:
    # Salvar conta no BD
    pass

for transaction in transactions:
    # Salvar transação no BD
    pass
"""


# ======== EXEMPLO 10: Fluxo com Erro e Retry ========

"""
Usuário coloca token inválido:

1️⃣ Usuário: "12345678901"  (falta o token depois de :)

2️⃣ Bot:
   ❌ Token Inter inválido!
   
   Formato esperado: CPF:token
   Exemplo: 12345678901:abc123def456...
   
   Dicas:
   • Copie o token completo (com toda a sequência)
   • Não adicione espaços
   • Se tiver ':', não remova
   
   Tente novamente:

3️⃣ Usuário: "12345678901:abc123def456ghi789"  (correto agora!)

4️⃣ Bot:
   ✅ Token de Inter Validado!
   
   🔐 Conexão segura estabelecida
   ...
"""


print("""
✅ Exemplos de token_auth.py carregados com sucesso!

Para testar no Telegram:
1. Use /conectar_token
2. Selecione seu banco
3. Siga as instruções
4. Cole o token

Para mais detalhes, veja: AUTENTICACAO_TOKEN_BANCOS.md
""")
