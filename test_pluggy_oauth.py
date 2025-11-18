#!/usr/bin/env python3
"""
Script de Teste Automático - Fluxo OAuth Pluggy
Executa todos os passos: link token → item → OAuth → polling → dados
"""
import os
import sys
import time
import webbrowser
import requests
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Carrega variáveis de ambiente
load_dotenv()

CLIENT_ID = os.getenv("PLUGGY_CLIENT_ID")
CLIENT_SECRET = os.getenv("PLUGGY_CLIENT_SECRET")
REDIRECT_URI = os.getenv("PLUGGY_REDIRECT_URI")

if not all([CLIENT_ID, CLIENT_SECRET, REDIRECT_URI]):
    print("❌ Erro: Configure PLUGGY_CLIENT_ID, PLUGGY_CLIENT_SECRET e PLUGGY_REDIRECT_URI no .env")
    sys.exit(1)

BASE_URL = "https://api.pluggy.ai"
api_key = None
api_key_expires_at = None

def get_api_key():
    """Obtém API Key da Pluggy"""
    global api_key, api_key_expires_at
    
    now = datetime.now()
    if api_key and api_key_expires_at and now < api_key_expires_at:
        return api_key
    
    print("🔑 Obtendo API Key...")
    response = requests.post(
        f"{BASE_URL}/auth",
        json={"clientId": CLIENT_ID, "clientSecret": CLIENT_SECRET},
        headers={"Content-Type": "application/json"},
        timeout=30
    )
    response.raise_for_status()
    
    api_key = response.json()["apiKey"]
    api_key_expires_at = now + timedelta(hours=23)
    print("✅ API Key obtida\n")
    return api_key

def make_request(method, endpoint, data=None, params=None):
    """Faz requisição HTTP para API Pluggy"""
    key = get_api_key()
    headers = {
        "X-API-KEY": key,
        "Content-Type": "application/json"
    }
    
    response = requests.request(
        method=method,
        url=f"{BASE_URL}{endpoint}",
        headers=headers,
        json=data,
        params=params,
        timeout=30
    )
    response.raise_for_status()
    return response.json()

print("=" * 70)
print("🚀 TESTE AUTOMÁTICO - FLUXO OAUTH PLUGGY")
print("=" * 70)
print()

# Passo 1: Listar conectores disponíveis
print("📝 Passo 1: Listando bancos com OAuth...")

try:
    result = make_request("GET", "/connectors", params={"countries": "BR"})
    connectors = result.get('results', [])
    oauth_connectors = [c for c in connectors if c.get('oauth', False) and c.get('type') in ('PERSONAL_BANK', 'BUSINESS_BANK')]
    
    if not oauth_connectors:
        print("❌ Nenhum conector com OAuth encontrado")
        sys.exit(1)
    
    print(f"✅ {len(oauth_connectors)} bancos encontrados com OAuth\n")
except Exception as e:
    print(f"❌ Erro ao listar conectores: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Passo 2: Escolher banco
print("📋 Passo 2: Escolha o banco...")
print("Bancos disponíveis:")
for i, conn in enumerate(oauth_connectors[:10], 1):  # Mostra primeiros 10
    print(f"  {i}. {conn['name']} (ID: {conn['id']})")
print()

# Solicita escolha
try:
    choice = input(f"Escolha um banco (1-{min(10, len(oauth_connectors))}): ").strip()
    connector_id = oauth_connectors[int(choice) - 1]["id"]
    connector_name = oauth_connectors[int(choice) - 1]["name"]
    print(f"✅ Selecionado: {connector_name} (ID: {connector_id})")
    print()
except (ValueError, IndexError):
    print("❌ Escolha inválida")
    sys.exit(1)

# Passo 3: Criar Item (conexão OAuth)
print("🔗 Passo 3: Criando Item (conexão OAuth)...")
cpf = input("Digite o CPF do titular (apenas números): ").strip()

try:
    item_data = {
        "connectorId": connector_id,
        "parameters": {"cpf": cpf}
    }
    
    item = make_request("POST", "/items", data=item_data)
    
    item_id = item["id"]
    
    print(f"✅ Item criado: {item_id}")
    print(f"✅ Status inicial: {item.get('status')}")
    print()
    
    # Verificar se precisa de ação do usuário (OAuth)
    user_action = item.get("userAction")
    
    if user_action and user_action.get("type") == "authorize":
        # Tem URL de autorização OAuth
        oauth_url = user_action.get("url")
        print("🌐 OAuth URL encontrada na resposta:")
        print(f"   {oauth_url}")
        print()
    else:
        # Conector já está sincronizando (alguns bancos fazem OAuth interno)
        print("⚠️  Este conector não retornou URL OAuth - pode estar usando fluxo automático")
        print(f"   Status: {item.get('status')}")
        print(f"   Aguarde a sincronização...")
        oauth_url = None
    
    print()
    
except Exception as e:
    print(f"❌ Erro ao criar Item: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Passo 4: Abrir navegador para OAuth (se necessário)
if oauth_url:
    print("🔐 Passo 4: Abrindo navegador para login no banco...")
    print("   → Faça login no banco quando a janela abrir")
    print("   → Após autorizar, o banco vai redirecionar para seu callback")
    print()

    open_browser = input("Deseja abrir o navegador agora? (s/n): ").strip().lower()
    if open_browser == "s":
        webbrowser.open(oauth_url)
    else:
        print(f"⚠️  Abra manualmente este link: {oauth_url}")

    print()
    print("⏳ Aguardando você completar o login no banco...")
    input("   Pressione ENTER depois de fazer login e autorizar ⏎")
    print()
else:
    print("⏩ Pulando abertura do navegador (OAuth automático)")
    print()

# Passo 5: Polling do Item até ficar HEALTHY
print("🔄 Passo 5: Verificando status do Item...")
print(f"   Consultando item {item_id}...")
print()

max_attempts = 60  # 5 minutos (60 x 5s)
attempt = 0
last_status = None
oauth_prompted = False

try:
    while attempt < max_attempts:
        item_status = make_request("GET", f"/items/{item_id}")
        current_status = item_status.get("status")
        status_detail = item_status.get("statusDetail", "")
        user_action = item_status.get("userAction")
        
        if current_status != last_status:
            detail_str = str(status_detail) if status_detail and not isinstance(status_detail, str) else status_detail
            print(f"   Status: {current_status} {('- ' + detail_str) if detail_str else ''}")
            last_status = current_status
            
            # Se virou WAITING_USER_INPUT, procurar URL OAuth
            if current_status == "WAITING_USER_INPUT" and not oauth_prompted:
                print()
                print("⚠️  AÇÃO NECESSÁRIA: Banco requer autorização OAuth!")
                print()
                
                # A URL pode estar em vários lugares
                auth_url = None
                
                # 1. Tentar em parameter.data (Open Finance comum)
                parameter = item_status.get("parameter", {})
                if parameter and parameter.get("type") == "oauth" and parameter.get("data"):
                    auth_url = parameter["data"]
                    print(f"🔗 URL de Autorização OAuth (Open Finance):")
                    print(f"   {auth_url}")
                    print()
                
                # 2. Tentar em userAction.url (fluxo alternativo)
                elif user_action and user_action.get("type") == "authorize" and user_action.get("url"):
                    auth_url = user_action["url"]
                    print(f"🔗 URL de Autorização:")
                    print(f"   {auth_url}")
                    print()
                
                if auth_url:
                    open_now = input("Deseja abrir no navegador? (s/n): ").strip().lower()
                    if open_now == "s":
                        webbrowser.open(auth_url)
                    
                    print()
                    input("⏎ Pressione ENTER após completar a autorização no banco...")
                    print()
                    print("🔄 Continuando verificação...")
                    oauth_prompted = True
                else:
                    print("❌ Não foi possível encontrar URL de autorização")
                    print(f"   Parameter: {parameter}")
                    print(f"   UserAction: {user_action}")
        
        # Status finais
        if current_status in ("UPDATED", "PARTIAL_SUCCESS"):
            print()
            print(f"✅ Item conectado com sucesso! Status: {current_status}")
            break
        
        if current_status in ("LOGIN_ERROR", "INVALID_CREDENTIALS", "ERROR", "SUSPENDED"):
            print()
            print(f"❌ Falha na conexão: {current_status} - {status_detail}")
            sys.exit(1)
        
        # Aguarda antes de consultar novamente
        time.sleep(5)
        attempt += 1
    
    if attempt >= max_attempts:
        print()
        print("⏰ Timeout: Item não ficou saudável em 5 minutos")
        print(f"   Status final: {last_status}")
        sys.exit(1)
        
except Exception as e:
    print(f"❌ Erro ao consultar status: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Passo 6: Buscar contas e transações
print()
print("=" * 70)
print("💰 Passo 6: Buscando dados bancários...")
print("=" * 70)
print()

try:
    # Contas
    print("📊 Contas encontradas:")
    accounts_result = make_request("GET", "/accounts", params={"itemId": item_id})
    accounts = accounts_result.get("results", [])
    
    if not accounts:
        print("   Nenhuma conta encontrada")
    else:
        for acc in accounts:
            balance = acc.get("balance", 0)
            currency = acc.get("currencyCode", "BRL")
            print(f"   • {acc.get('name')} - Tipo: {acc.get('type')} - Saldo: {currency} {balance:.2f}")
    
    print()
    
    # Transações (últimas 10)
    print("📈 Últimas transações:")
    if accounts:
        account_id = accounts[0]["id"]
        txn_result = make_request("GET", "/transactions", params={"accountId": account_id, "pageSize": 10})
        transactions = txn_result.get("results", [])
        
        if not transactions:
            print("   Nenhuma transação encontrada")
        else:
            for txn in transactions[:10]:
                date = txn.get("date", "")[:10]
                desc = txn.get("description", "N/A")
                amount = txn.get("amount", 0)
                print(f"   • {date} - {desc} - R$ {amount:.2f}")
    else:
        transactions = []
        print("   Sem contas para buscar transações")
    
    print()
    print("=" * 70)
    print("✅ TESTE CONCLUÍDO COM SUCESSO!")
    print("=" * 70)
    print()
    print(f"📋 Resumo:")
    print(f"   Item ID: {item_id}")
    print(f"   Banco: {connector_name}")
    print(f"   Status: {current_status}")
    print(f"   Contas: {len(accounts)}")
    print(f"   Transações: {len(transactions)}")
    print()
    
except Exception as e:
    print(f"❌ Erro ao buscar dados: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
