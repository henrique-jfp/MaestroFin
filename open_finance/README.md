# 🏦 Open Finance - Integração com Pluggy

## 📋 Visão Geral

Integração com **Pluggy API** (Open Finance do Banco Central) para conectar com bancos e cartões de crédito, obtendo dados oficiais em tempo real.

---

## ✨ Funcionalidades

### **Para o Usuário:**
- ✅ `/conectar_banco` - Conectar conta bancária via Open Finance
- ✅ `/minhas_contas` - Listar todas as contas conectadas
- ✅ `/saldo` - Ver saldo consolidado em tempo real
- ✅ `/extrato` - Ver transações recentes (últimos 30 dias)
- ✅ `/desconectar_banco` - Remover conexão

### **Automático:**
- 🔄 Sincronização automática a cada 6 horas
- 🔄 Sincronização diária completa às 6h da manhã
- 📊 Atualização de saldos e transações
- 🔔 (Futuro) Notificações de novos gastos

---

## 🚀 Setup

### **1. Criar conta Pluggy:**

Acesse: https://dashboard.pluggy.ai/signup

- Tier gratuito: **100 conexões/mês**
- Sandbox ilimitado para testes

### **2. Obter credenciais:**

No dashboard Pluggy:
1. Ir em **API Keys**
2. Copiar **Client ID**
3. Copiar **Client Secret**

### **3. Configurar variáveis de ambiente:**

Adicionar no Railway/Render:

```bash
PLUGGY_CLIENT_ID=seu_client_id_aqui
PLUGGY_CLIENT_SECRET=seu_client_secret_aqui
```

### **4. Migração de banco de dados:**

As tabelas são criadas automaticamente na primeira execução:
- `bank_connections` - Conexões bancárias
- `bank_accounts` - Contas (corrente, poupança, cartão)
- `bank_transactions` - Transações sincronizadas

---

## 🏗️ Arquitetura

```
open_finance/
├── __init__.py              # Módulo principal
├── pluggy_client.py         # Cliente HTTP Pluggy API
├── bank_connector.py        # Gerenciador de conexões
├── data_sync.py             # Sincronização automática
└── README.md                # Esta documentação

gerente_financeiro/
└── open_finance_handler.py  # Comandos Telegram
```

---

## 📊 Fluxo de Dados

### **1. Usuário conecta banco:**
```
/conectar_banco
  ↓
Seleciona banco (Pluggy lista 150+ instituições)
  ↓
Insere credenciais (CPF + senha)
  ↓
Pluggy autentica e cria "Item" (conexão)
  ↓
Bot salva conexão no banco de dados
  ↓
Sincroniza contas e transações (últimos 30 dias)
```

### **2. Sincronização automática:**
```
APScheduler dispara job (6h ou a cada 6h)
  ↓
DataSynchronizer.sync_all_connections()
  ↓
Para cada conexão ativa:
  - Atualiza saldos (GET /accounts)
  - Busca novas transações (GET /transactions)
  - Salva no banco local
```

### **3. Usuário consulta dados:**
```
/saldo ou /extrato
  ↓
BankConnector consulta banco local
  ↓
Retorna dados já sincronizados (rápido!)
```

---

## 🔐 Segurança

### **Credenciais:**
- ❌ **NÃO são armazenadas** pelo bot
- ✅ Enviadas direto para Pluggy via HTTPS
- ✅ Pluggy usa OAuth 2.0 + criptografia
- ✅ Mensagem com senha é deletada automaticamente

### **Tokens de acesso:**
- ✅ `item_id` salvo no banco (identificador único)
- ✅ Pluggy gerencia refresh tokens automaticamente
- ✅ Conexão pode ser removida a qualquer momento

### **Conformidade:**
- ✅ Open Finance regulamentado pelo Banco Central
- ✅ Pluggy certificado pela ABCD (Associação Brasileira de Crédito Digital)
- ✅ LGPD compliant

---

## 🏦 Bancos Suportados

**Principais (150+ instituições):**
- 💳 Nubank
- 🟠 Banco Inter
- 🔷 C6 Bank
- 🟡 Itaú
- 🔴 Bradesco
- 🟢 Santander
- 🔵 Caixa
- ⚫ Banco do Brasil
- 🟣 PagBank
- E muito mais...

Ver lista completa: https://docs.pluggy.ai/docs/connectors

---

## 📖 Exemplos de Uso

### **Python - Listar bancos disponíveis:**
```python
from open_finance.pluggy_client import PluggyClient

client = PluggyClient()
bancos = client.list_connectors(country="BR")

for banco in bancos[:10]:
    print(f"{banco['name']} (ID: {banco['id']})")
```

### **Python - Criar conexão:**
```python
from open_finance.bank_connector import BankConnector

connector = BankConnector()

connection = connector.create_connection(
    user_id=123456789,
    connector_id=201,  # Nubank
    credentials={"user": "12345678900", "password": "minhasenha"}
)

print(f"Conectado: {connection['connector_name']}")
```

### **Python - Consultar saldo:**
```python
total = connector.get_total_balance(user_id=123456789)
print(f"Saldo total: R$ {total:,.2f}")
```

---

## 🔧 Troubleshooting

### **Erro: "Credenciais Pluggy não encontradas"**
```bash
# Verificar variáveis de ambiente
echo $PLUGGY_CLIENT_ID
echo $PLUGGY_CLIENT_SECRET

# Se vazias, configurar no Railway/Render
```

### **Erro: "HTTP 401 Unauthorized"**
```python
# Client ID/Secret inválidos
# Verificar no dashboard Pluggy se credenciais estão corretas
```

### **Erro: "LOGIN_ERROR" ao conectar banco**
```
# Credenciais do banco incorretas
# Usuário deve tentar novamente com senha correta
```

### **Sincronização não funciona**
```python
# Verificar logs do APScheduler
# Verificar se schedule_daily_sync() foi chamado no startup do bot
```

---

## 📚 Documentação Pluggy

- 📖 Docs: https://docs.pluggy.ai
- 🔌 API Reference: https://docs.pluggy.ai/docs/api
- 💬 Suporte: support@pluggy.ai
- 📊 Dashboard: https://dashboard.pluggy.ai

---

## 🚀 Próximas Funcionalidades

- [ ] Notificações de novos gastos
- [ ] Categorização automática com IA
- [ ] Gráficos de gastos por categoria
- [ ] Previsão de saldo futuro
- [ ] Alertas de gastos incomuns
- [ ] Suporte a investimentos (CDB, ações, fundos)
- [ ] Exportar extrato para Excel/PDF
- [ ] Análise de crédito automática

---

## ⚠️ Limitações Tier Gratuito

**Pluggy Free Tier:**
- ✅ 100 conexões ativas/mês
- ✅ Sandbox ilimitado
- ❌ Histórico limitado (12 meses)
- ❌ Sem webhooks

**Para produção:**
- Plano Starter: $99/mês (500 conexões)
- Plano Growth: $299/mês (2000 conexões)
- Enterprise: Customizado

---

## 📝 Changelog

### v1.0.0 (17/11/2025)
- ✅ Integração inicial com Pluggy
- ✅ Comandos básicos (conectar, saldo, extrato)
- ✅ Sincronização automática
- ✅ Suporte a 150+ bancos brasileiros
