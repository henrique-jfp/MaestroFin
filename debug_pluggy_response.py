#!/usr/bin/env python3
"""
🔍 Debug: Inspecionar EXATAMENTE o que Pluggy retorna
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

def debug_pluggy_response():
    print("\n" + "="*80)
    print("🔍 DEBUG: Resposta Completa do Pluggy")
    print("="*80 + "\n")
    
    client = PluggyClient()
    
    # Listar conectores
    connectors = client.list_connectors(country="BR")
    
    # Inter 823
    inter = None
    for conn in connectors:
        if conn.get('id') == 823:
            inter = conn
            break
    
    if not inter:
        print("❌ Inter não encontrado!")
        return
    
    print(f"✅ Usando conector: {inter.get('name')} (ID: {inter.get('id')})\n")
    
    # Criar item
    print("🔗 Criando item (pode levar alguns segundos)...\n")
    
    # Usar um CPF válido (formato correto, mas não precisa ser real para teste)
    # Formato: XXX.XXX.XXX-XX
    test_cpf = "123.456.789-10"
    
    try:
        print(f"📝 Enviando CPF: {test_cpf}\n")
        item = client.create_item(
            connector_id=inter['id'],
            credentials={"cpf": test_cpf}
        )
        
        print("📋 RESPOSTA CREATE_ITEM (JSON Completo):\n")
        print(json.dumps(item, indent=2, default=str))
        
        print("\n" + "="*80)
        print("🔑 CAMPOS CRÍTICOS:\n")
        
        critical_fields = [
            'id', 'status', 'statusDetail', 'nextStep',
            'url', 'redirectUrl', 'connectUrl', 'authUrl',
            'deepLink', 'webhookUrl'
        ]
        
        for field in critical_fields:
            if field in item:
                value = item[field]
                if value:
                    print(f"✅ {field}: {value}")
                else:
                    print(f"⚠️  {field}: (vazio/null)")
            else:
                print(f"❌ {field}: NÃO PRESENTE")
        
        print("\n" + "="*80)
        print("⏳ AGUARDANDO STATUS (polling por 30 segundos)...\n")
        
        item_id = item['id']
        
        for attempt in range(15):
            time.sleep(2)
            
            status_item = client.get_item(item_id)
            status = status_item.get('status')
            
            print(f"[{attempt+1}/15] Status: {status}")
            
            # Imprimir campos importantes a cada mudança de status
            if status == 'WAITING_USER_INPUT':
                print("\n🔴 WAITING_USER_INPUT detectado!")
                print("\n📋 RESPOSTA GET_ITEM (JSON Completo):\n")
                print(json.dumps(status_item, indent=2, default=str))
                
                print("\n" + "="*80)
                print("🔑 CAMPOS COM URL:\n")
                
                for field in critical_fields:
                    if field in status_item:
                        value = status_item[field]
                        if value:
                            print(f"✅ {field}: {value}")
                        else:
                            print(f"⚠️  {field}: (vazio/null)")
                    else:
                        print(f"❌ {field}: NÃO PRESENTE")
                
                break
        
        print("\n" + "="*80)
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    debug_pluggy_response()
