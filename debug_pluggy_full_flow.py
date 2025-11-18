#!/usr/bin/env python3
"""
🔍 Debug: Rastrear fluxo completo do Pluggy até sincronização
Descobre em qual etapa a sincronização falha
"""

import os
import json
import time
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
dotenv_path = os.path.join(basedir, '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)

from open_finance.pluggy_client import PluggyClient

def debug_full_flow():
    """Rastreia fluxo completo: criar item → esperar → sincronizar"""
    
    print("\n" + "="*80)
    print("🔍 DEBUG: FLUXO COMPLETO DO PLUGGY")
    print("="*80 + "\n")
    
    client = PluggyClient()
    
    # ========== ETAPA 1: Listar conectores ==========
    print("📋 ETAPA 1: Listando conectores...")
    print("-" * 80)
    
    try:
        connectors = client.list_connectors(country="BR")
        print(f"✅ {len(connectors)} conectores encontrados\n")
        
        # Encontrar Inter
        inter = None
        for conn in connectors:
            if conn.get('id') == 823:
                inter = conn
                break
        
        if not inter:
            print("❌ Inter ID 823 não encontrado!")
            return
        
        print(f"✅ Inter encontrado: {inter.get('name')} (ID: {inter.get('id')})")
        print(f"   Credenciais obrigatórias: {inter.get('credentials')}\n")
        
    except Exception as e:
        print(f"❌ Erro: {e}\n")
        return
    
    # ========== ETAPA 2: Criar item (conexão) ==========
    print("📋 ETAPA 2: Criando item...")
    print("-" * 80)
    
    # ⚠️ USE UM CPF REAL E SENHA REAL PARA TESTAR
    # Ou use um CPF/senha fake para ver o erro
    cpf = input("Digite seu CPF (apenas números): ").strip()
    senha = input("Digite sua senha: ").strip()
    
    if not cpf or not senha:
        print("❌ CPF ou senha vazio!")
        return
    
    try:
        item = client.create_item(
            connector_id=inter['id'],
            credentials={"cpf": cpf, "password": senha}
        )
        item_id = item.get('id')
        print(f"✅ Item criado: {item_id}\n")
        
        print("📄 Resposta COMPLETA do create_item():")
        print(json.dumps(item, indent=2, default=str))
        print()
        
    except Exception as e:
        print(f"❌ Erro ao criar item: {e}\n")
        return
    
    # ========== ETAPA 3: Polling até WAITING_USER_INPUT ==========
    print("\n" + "="*80)
    print("📋 ETAPA 3: Aguardando status WAITING_USER_INPUT...")
    print("-" * 80)
    
    start_time = time.time()
    for attempt in range(30):  # 30 tentativas com 2s de intervalo = 60s
        try:
            item = client.get_item(item_id)
            status = item.get('status')
            elapsed = time.time() - start_time
            
            print(f"[{elapsed:6.1f}s] Tentativa {attempt+1}: Status = {status}")
            
            if status == "WAITING_USER_INPUT":
                print(f"\n✅ Status WAITING_USER_INPUT atingido em {elapsed:.1f}s\n")
                print("📄 Item status:")
                print(json.dumps(item, indent=2, default=str))
                
                # Aqui o usuário deveria clicar no link do Pluggy
                print("\n" + "="*80)
                print("👉 AÇÃO NECESSÁRIA DO USUÁRIO:")
                print("-" * 80)
                print(f"Abra este link: https://dashboard.pluggy.ai/items/{item_id}/authentication")
                print("E faça login no Inter com seu CPF e senha")
                print("Autorize o acesso ao Maestro Financeiro")
                print("\nDepois, volta aqui e pressiona ENTER para continuar...")
                input("Pressione ENTER quando tiver autorizado... ")
                
                break
            
            time.sleep(2)
            
        except Exception as e:
            print(f"❌ Erro ao verificar status: {e}")
            return
    
    # ========== ETAPA 4: Polling após autorização (CRITICAL!) ==========
    print("\n" + "="*80)
    print("📋 ETAPA 4: Aguardando sincronização (após autorização no banco)...")
    print("-" * 80)
    
    start_time = time.time()
    for attempt in range(30):  # 30 tentativas com 2s = 60s
        try:
            item = client.get_item(item_id)
            status = item.get('status')
            elapsed = time.time() - start_time
            
            print(f"[{elapsed:6.1f}s] Tentativa {attempt+1}: Status = {status}")
            
            if status in {"HEALTHY", "PARTIAL_SUCCESS"}:
                print(f"\n✅ Status {status} atingido em {elapsed:.1f}s!")
                print("🎉 SUCESSO! A sincronização funcionou!\n")
                print("📄 Item final:")
                print(json.dumps(item, indent=2, default=str))
                
                # ========== ETAPA 5: Buscar contas ==========
                print("\n" + "="*80)
                print("📋 ETAPA 5: Buscando contas...")
                print("-" * 80)
                
                try:
                    accounts = client.list_accounts(item_id)
                    print(f"✅ {len(accounts)} contas encontradas:\n")
                    
                    for acc in accounts:
                        print(f"  - {acc.get('name')} (ID: {acc.get('id')})")
                        print(f"    Tipo: {acc.get('type')}")
                        print(f"    Número: {acc.get('number')}")
                        print(f"    Saldo: {acc.get('balance')} {acc.get('currency')}\n")
                    
                except Exception as e:
                    print(f"❌ Erro ao buscar contas: {e}\n")
                
                return
            
            elif status in {"LOGIN_ERROR", "INVALID_CREDENTIALS", "ERROR", "SUSPENDED"}:
                print(f"\n❌ Erro no status: {status}")
                print(f"Detalhe: {item.get('statusDetail')}")
                return
            
            time.sleep(2)
            
        except Exception as e:
            print(f"❌ Erro: {e}")
            return
    
    print("\n❌ Tempo esgotado! O Pluggy não sincronizou em 60 segundos.")
    print("Isso significa que o Pluggy não conseguiu acessar o banco.")
    print("\nPossíveis causas:")
    print("1. Pluggy ainda processando (pode levar mais tempo)")
    print("2. Banco bloqueou/rejeitou a conexão")
    print("3. Credenciais inválidas")
    print("4. O banco (Inter) mudou a API e Pluggy ainda não atualizou")

if __name__ == '__main__':
    debug_full_flow()
