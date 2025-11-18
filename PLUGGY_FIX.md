# 🔧 CORREÇÃO PLUGGY - PROBLEMA DE CONECTORES

## ⚠️ Problema Identificado

**Por que nenhuma solicitação de conexão chegava aos bancos?**

O código estava usando o **conector incorreto** do Pluggy! 

### Exemplo: Inter

Pluggy oferece **2 conectores diferentes para o Inter**:

1. **ID 215** - Inter (Dados Públicos)
   - ❌ SEM credenciais requeridas
   - ❌ Não oferece Open Finance pessoal
   - ❌ Não pode acessar contas do usuário

2. **ID 823** - Inter (Open Finance)
   - ✅ Requer CPF
   - ✅ Oferece Open Finance real
   - ✅ Acessa contas, cartões e transações do usuário

**O bug:** Quando o Pluggy listava conectores, o ID 215 vinha primeiro, e o código selecionava ele automaticamente. Resultado: `create_item()` era chamado com o conector errado, que não conseguia gerar nenhuma solicitação de Open Finance.

---

## ✅ Solução Implementada

### 1. Criar `open_finance/connector_map.py`

Mapeamento explícito dos conectores preferidos:

```python
BANK_CONNECTOR_MAP = {
    "inter": {
        "preferred_id": 823,  # ✅ Open Finance
        "fallback_ids": [215]  # ❌ Fallback (dados públicos)
    },
    "itau": {
        "preferred_id": 601,  # ✅ CPF (Open Finance)
        "fallback_ids": [201]  # ❌ Legacy (Agência/Conta/Senha)
    },
    "bradesco": {
        "preferred_id": 603,  # ✅ CPF (Open Finance)
        "fallback_ids": [203]  # ❌ Legacy (Agência/Conta/Senha/Token)
    },
    "nubank": {
        "preferred_id": 612,  # ✅ CPF (Open Finance)
    },
    "caixa": {
        "preferred_id": 619,  # ✅ CPF (Open Finance)
        "fallback_ids": [219, 783]  # ❌ Legacy
    },
    "santander": {
        "preferred_id": 608,  # ✅ CPF (Open Finance)
        "fallback_ids": [208]  # ❌ Legacy
    }
}
```

### 2. Adicionar Credenciais ao `config.py`

```python
# ----- PLUGGY / OPEN FINANCE -----
PLUGGY_CLIENT_ID = os.getenv("PLUGGY_CLIENT_ID")
PLUGGY_CLIENT_SECRET = os.getenv("PLUGGY_CLIENT_SECRET")
```

### 3. Refatorar Seleção de Conectores

**Antes:** Código complexo que tentava filtar por nome (frágil)

**Depois:** Usa `filter_and_sort_connectors()` que retorna conectores na ordem correta

---

## 🧪 Como Verificar

### 1. Teste Rápido das Credenciais

```bash
python3 test_pluggy.py
```

Esperado:
```
✅ API Key obtida: eyJhbGciOi...
✅ 152 conectores encontrados

🏦 Principais bancos suportados:
   ✅ Inter                          (ID: 215, Credenciais: 0)
   ✅ Inter                          (ID: 823, Credenciais: 1)
   ✅ Itaú                           (ID: 601, Credenciais: 1)
   ... etc
```

### 2. Analisar Detalhes dos Conectores

```bash
python3 analyze_connectors.py
```

Mostra quais credenciais cada conector requer.

### 3. Testar no Bot

```
/conectar_banco
```

Agora deve mostrar **apenas os conectores corretos** com Open Finance real.

---

## 📊 Comparação: Antes vs Depois

| Banco | Antes | Depois |
|-------|--------|--------|
| **Inter** | ID 215 (sem login) ❌ | ID 823 (CPF) ✅ |
| **Itaú** | ID 201 (Agência/Conta/Senha) | ID 601 (CPF) ✅ |
| **Bradesco** | ID 203 (Agência/Conta/Senha/Token) | ID 603 (CPF) ✅ |
| **Nubank** | ID 612 (CPF) ✅ | ID 612 (CPF) ✅ |
| **Caixa** | ID 219 (User/Senha) | ID 619 (CPF) ✅ |
| **Santander** | ID 208 (CPF/Senha) | ID 608 (CPF) ✅ |

---

## 🚀 Próximos Passos

### 1. Deploy em Produção

Certifique-se de que estas variáveis estão configuradas no **Render**:

```
PLUGGY_CLIENT_ID=4cb69d1c-cbf6-4487-a7d2-1577dd0692d9
PLUGGY_CLIENT_SECRET=90ee2d78-c673-4b65-87cc-24d214e0fa05
```

### 2. Testar com Usuário Real

1. Abrir bot no Telegram
2. Usar `/conectar_banco`
3. Selecionar um banco
4. Informar CPF
5. **Esperado:** Receber solicitação de autorização no app do banco

### 3. Monitorar Logs

Esperado ver nos logs:

```
🔗 Criando conexão com conector 823...  ← Correto!
✅ Item criado: 5e707fbc-...
🏦 Sincronizando contas da conexão 1...
✅ 2 contas sincronizadas
```

---

## 🔍 Debugging

Se ainda não funcionar:

### Check 1: Credenciais Pluggy

```python
from config import PLUGGY_CLIENT_ID, PLUGGY_CLIENT_SECRET
print(f"Client ID: {PLUGGY_CLIENT_ID}")  # Deve ter valor
print(f"Secret: {PLUGGY_CLIENT_SECRET}")  # Deve ter valor
```

### Check 2: Conectores Disponíveis

```python
from open_finance.pluggy_client import PluggyClient
client = PluggyClient()
connectors = client.list_connectors(country="BR")
for c in connectors:
    if 'inter' in c.get('name', '').lower():
        print(f"ID {c['id']}: {c['name']} - {len(c.get('credentials', []))} creds")
```

### Check 3: Criar Item de Teste

```python
from open_finance.bank_connector import BankConnector
connector = BankConnector()

# Tentar criar conexão com credentials reais
try:
    result = connector.create_connection(
        user_id=123456789,  # Seu Telegram ID
        connector_id=823,   # Inter Open Finance
        credentials={"cpf": "12345678901"}
    )
    print(f"✅ Item criado: {result}")
except Exception as e:
    print(f"❌ Erro: {e}")
```

---

## 📞 Suporte Pluggy

Se o erro persistir, verifique:

- **Documentação:** https://docs.pluggy.ai
- **Status da API:** https://api.pluggy.ai/status
- **Dashboard Pluggy:** Verifique se seu app está marcado como "Active"

---

## 📝 Arquivos Modificados

- ✅ `config.py` - Adicionado PLUGGY_CLIENT_ID e PLUGGY_CLIENT_SECRET
- ✅ `open_finance/connector_map.py` - Novo mapeamento de conectores
- ✅ `gerente_financeiro/open_finance_handler.py` - Usar novo mapeamento
- ✅ `test_pluggy.py` - Script para testar credenciais
- ✅ `analyze_connectors.py` - Analisar conectores disponíveis
