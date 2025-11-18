#!/usr/bin/env python3
"""
🔍 Investigar resposta completa do Pluggy
Mostra TODOS os campos retornados pelo Pluggy ao criar um item
"""

import os
import json
from dotenv import load_dotenv

# Carregar .env
basedir = os.path.abspath(os.path.dirname(__file__))
dotenv_path = os.path.join(basedir, '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)

from open_finance.pluggy_client import PluggyClient

def investigate_pluggy_response():
    """Investiga resposta completa do Pluggy"""
    
    print("\n" + "="*80)
    print("🔍 INVESTIGANDO RESPOSTA COMPLETA DO PLUGGY")
    print("="*80 + "\n")
    
    client = PluggyClient()
    
    # Listar conectores
    print("📋 Listando conectores...")
    connectors = client.list_connectors(country="BR")
    
    # Encontrar Inter (ID 823)
    inter = None
    for conn in connectors:
        if conn.get('id') == 823:
            inter = conn
            break
    
    if not inter:
        print("❌ Inter ID 823 não encontrado!")
        return
    
    print(f"✅ Encontrado: {inter.get('name')} (ID: {inter.get('id')})")
    print(f"   Credenciais: {inter.get('credentials')}\n")
    
    # Criar item com CPF fake para ver resposta completa
    print("🔗 Criando item (conexão) com CPF fake...")
    print("   CPF: 12345678901 (fake, para teste)\n")
    
    try:
        item_response = client.create_item(
            connector_id=inter['id'],
            credentials={"cpf": "12345678901"}
        )
        
        print("📋 RESPOSTA COMPLETA DO PLUGGY:\n")
        print(json.dumps(item_response, indent=2, default=str))
        
        print("\n" + "="*80)
        print("🔑 CAMPOS IMPORTANTES:\n")
        
        important_fields = [
            'id', 'status', 'statusDetail', 'nextStep',
            'redirectUrl', 'url', 'deepLink', 'webhook',
            'parameterForm', 'connectorInsights'
        ]
        
        for field in important_fields:
            if field in item_response:
                value = item_response[field]
                if isinstance(value, dict):
                    print(f"✅ {field}: <dict com {len(value)} chaves>")
                    for k, v in value.items():
                        print(f"     - {k}: {str(v)[:60]}...")
                elif isinstance(value, list):
                    print(f"✅ {field}: <lista com {len(value)} itens>")
                else:
                    print(f"✅ {field}: {value}")
            else:
                print(f"❌ {field}: NÃO PRESENTE")
        
        # Buscar o item para ver status completo
        print("\n" + "="*80)
        print("⏳ VERIFICANDO STATUS DO ITEM (alguns segundos)...\n")
        
        import time
        for i in range(5):
            item_status = client.get_item(item_response['id'])
            print(f"Tentativa {i+1}:")
            print(f"  Status: {item_status.get('status')}")
            print(f"  NextStep: {item_status.get('nextStep')}")
            print(f"  RedirectUrl: {item_status.get('redirectUrl')}")
            print(f"  URL: {item_status.get('url')}")
            
            if item_status.get('redirectUrl') or item_status.get('url'):
                print(f"\n✅ LINK ENCONTRADO!")
                break
            
            time.sleep(2)
        
        print("\n" + "="*80)
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    investigate_pluggy_response()
