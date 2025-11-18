# 🏦 Alternativas de Open Banking para Brasil (se Pluggy falhar)

## 🔴 Diagnóstico: Por que Pluggy pode estar falhando?

1. **Pluggy parou de funcionar com Inter**: Possível API breaking change
2. **Timeout na sincronização**: Pluggy esperando resposta do banco
3. **Credenciais rejeitadas**: Inter mudou validação
4. **Rate limiting**: Pluggy tendo requests bloqueadas pelo Inter

## ✅ Alternativas Disponíveis

### 1. **Plaid Brasil** (MELHOR)
- **Suporte**: Inter ✅, Itaú ✅, Bradesco ✅, Caixa ✅
- **API**: Oficial e estável
- **Documentação**: Excelente
- **Custo**: ~$0.25-$0.50 por conexão
- **Dados**: Contas, transações, saldo real-time
- **Link**: https://plaid.com/br/

**Desvantagem**: Pago (Pluggy também é pago)

```python
from plaid import ApiClient
from plaid.model.link_token_create_request import LinkTokenCreateRequest

client = ApiClient()
request = LinkTokenCreateRequest(
    user={"client_user_id": str(user_id)},
    client_name="Maestro Financeiro",
    user_language="pt-BR",
    country_codes=["BR"],
    language="pt",
)
response = client.link_token_create(request)
link_token = response['link_token']  # Usar no frontend
```

### 2. **Easybank (Open Finance Brasil)**
- **Suporte**: Todos os bancos que aderiram ao PIX/Open Finance
- **Documentação**: https://developers.easybank.com.br/
- **Custo**: Gratuito (?? Verificar)
- **Dados**: Contas, transações, saldo

```python
# Autenticação OAuth2
import requests

code = request.GET.get('code')  # Recebido do redirect
response = requests.post('https://api.easybank.com.br/oauth/token', json={
    'grant_type': 'authorization_code',
    'code': code,
    'client_id': CLIENT_ID,
    'client_secret': CLIENT_SECRET,
})
access_token = response.json()['access_token']
```

### 3. **Asaas** (Pagamentos + Open Banking)
- **Suporte**: Contas de usuários
- **API**: https://docs.asaas.com/
- **Custo**: Pago por transação
- **Melhor para**: Pagamentos, não muito para consulta

### 4. **OFX (Open File Format)** ❌ Deprecado
- ~~Protocolo legado para exportar extratos~~
- Maioria dos bancos descontinuou

### 5. **Web Scraping + RPA** (Último Recurso) ⚠️
- **Ferramentas**: Selenium, Playwright, Puppeteer
- **Risco**: Violação de ToS, bloqueio IP, conta banida
- **Confiabilidade**: Baixa (banco pode mudar UI)
- **Performance**: Muito lenta (10-30s por request)

```python
from selenium import webdriver
from selenium.webdriver.common.by import By

driver = webdriver.Chrome()
driver.get("https://appinter.inter.co/login")
# ... preencher CPF, senha, capcha...
# ... navegar até extrato...
# ... extrair dados...
```

### 6. **Integração Manual com Inter** (Viável!)
- Inter pode ter uma API B2B não pública
- Entrar em contato: dev@inter.co
- Possível contrato especial para aplicações

```python
# Se Inter disponibilizar API:
response = requests.get(
    'https://api.inter.co/v1/accounts',
    headers={'Authorization': f'Bearer {inter_token}'}
)
accounts = response.json()['accounts']
```

## 🏆 Ranking de Viabilidade

| Alternativa | Facilidade | Custo | Confiabilidade | Suporte | Recomendação |
|---|---|---|---|---|---|
| **Plaid Brasil** | ⭐⭐⭐⭐⭐ | $ | ⭐⭐⭐⭐⭐ | Ótimo | 🥇 **USE ISSO** |
| **Easybank** | ⭐⭐⭐⭐ | Gratuito? | ⭐⭐⭐⭐ | Bom | 🥈 Alternativa |
| **Asaas** | ⭐⭐⭐⭐ | $ | ⭐⭐⭐⭐ | Ótimo | Para pagamentos |
| **Inter Direct API** | ⭐ | Grátis | ? | ? | Contactar |
| **Web Scraping** | ⭐⭐ | Grátis | ⭐⭐ | Nenhum | 🔴 **NÃO USE** |

## 🔄 Plano de Ação

### Cenário 1: Pluggy NUNCA Sincroniza
```
1. Confirmar com debug_pluggy_full_flow.py
   → Se status nunca muda para CONNECTED em 60s
   → Pluggy está quebrado com Inter
   
2. Migrar para Plaid:
   a. Criar conta em plaid.com/br
   b. Gerar Client ID + Secret
   c. Implementar Link Widget (frontend)
   d. Substituir open_finance/pluggy_client.py → plaid_client.py
   e. Manter mesma structure de dados no DB
   
3. Testes:
   a. Testar com cada banco
   b. Verificar se dados batem
   c. Deploy gradual
```

### Cenário 2: Pluggy Funciona Depois de X Minutos
```
1. Problema: Timeout muito curto (90s)
2. Solução: Aumentar timeout e/ou fazer polling assíncrono
   a. Alterar _wait_until_ready() timeout: 90s → 600s (10 min)
   b. Ou usar job worker (celery/APScheduler) para polling
   c. Notificar usuário quando conectado
```

### Cenário 3: Pluggy Funciona Mas Dados Estão Errados
```
1. Verificar connector_map.py - IDs do Inter estão corretos?
2. Verificar se Pluggy está retornando campos corretos
3. Debug com debug_pluggy_full_flow.py para ver JSON completo
4. Abrir issue no GitHub do Pluggy
```

## 📝 Implementação Plaid (Rápido)

### Passo 1: Setup
```bash
pip install plaid-python
```

### Passo 2: Arquivo novo - plaid_client.py
```python
from plaid import ApiClient
from plaid.configuration import Configuration

config = Configuration(
    host='https://sandbox.plaid.com',  # ou production
    api_key=os.getenv('PLAID_SECRET_KEY'),
)
client = ApiClient(config)

def create_link_token(user_id: str):
    """Cria token para Plaid Link Widget"""
    request = LinkTokenCreateRequest(
        user={"client_user_id": str(user_id)},
        client_name="Maestro Financeiro",
        country_codes=["BR"],
    )
    response = client.link_token_create(request)
    return response['link_token']

def exchange_token(public_token: str):
    """Troca public_token por access_token"""
    request = ItemPublicTokenExchangeRequest(
        public_token=public_token
    )
    response = client.item_public_token_exchange(request)
    return response['access_token']

def get_accounts(access_token: str):
    """Lista contas do usuário"""
    request = AccountsGetRequest(
        access_token=access_token
    )
    response = client.accounts_get(request)
    return response['accounts']
```

### Passo 3: Integração com Handler
```python
# In handler
async def connect_bank(self, ...):
    link_token = plaid_client.create_link_token(user_id)
    
    # Enviar para frontend (se tiver web)
    # Ou abrir como webview no Telegram
```

## ⚠️ Decisão: Qual Caminho Seguir?

**RECOMENDAÇÃO**: 
1. Primeiro: Rodar `debug_pluggy_full_flow.py` com credenciais reais
2. Se não sincronizar em 60s → **Migrar para Plaid**
3. Se sincronizar → Aumentar timeout e continuar com Pluggy

**Tempo Estimado**:
- Debug: 5 minutos
- Migração Plaid: 2-3 horas
- Testes: 1 hora

---

**Quer que eu implemente alguma dessas alternativas?**
