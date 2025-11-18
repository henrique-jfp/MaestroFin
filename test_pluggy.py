#!/usr/bin/env python3
"""
🧪 Script de teste para Pluggy API
Testa se as credenciais estão funcionando
"""

import os
import sys
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Carregar variáveis de ambiente
try:
    from dotenv import load_dotenv
    basedir = os.path.abspath(os.path.dirname(__file__))
    dotenv_path = os.path.join(basedir, '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path)
        logger.info(f"✅ Variáveis de ambiente carregadas de {dotenv_path}")
except Exception as e:
    logger.warning(f"⚠️ Erro ao carregar .env: {e}")

# Testar Pluggy
from open_finance.pluggy_client import PluggyClient

def test_pluggy():
    """Testa a comunicação com Pluggy"""
    
    print("\n" + "="*60)
    print("🧪 TESTE PLUGGY API")
    print("="*60 + "\n")
    
    # Verificar credenciais
    client_id = os.getenv('PLUGGY_CLIENT_ID')
    client_secret = os.getenv('PLUGGY_CLIENT_SECRET')
    
    print(f"📋 Credenciais carregadas:")
    print(f"   PLUGGY_CLIENT_ID: {client_id[:10]}... (truncado)" if client_id else "   ❌ PLUGGY_CLIENT_ID não encontrado")
    print(f"   PLUGGY_CLIENT_SECRET: {client_secret[:10]}... (truncado)" if client_secret else "   ❌ PLUGGY_CLIENT_SECRET não encontrado")
    
    if not client_id or not client_secret:
        print("\n❌ Credenciais não configuradas!")
        return False
    
    try:
        # Inicializar cliente
        print("\n🔌 Inicializando cliente Pluggy...")
        client = PluggyClient(client_id=client_id, client_secret=client_secret)
        print("✅ Cliente inicializado com sucesso")
        
        # Testar autenticação
        print("\n🔑 Testando autenticação...")
        api_key = client._get_api_key()
        print(f"✅ API Key obtida: {api_key[:10]}... (truncado)")
        
        # Listar conectores
        print("\n📋 Listando conectores disponíveis para BR...")
        connectors = client.list_connectors(country="BR")
        print(f"✅ {len(connectors)} conectores encontrados\n")
        
        # Exibir bancos principais
        print("🏦 Principais bancos suportados:")
        
        main_banks = {
            "inter": None,
            "itaú": None,
            "itau": None,
            "bradesco": None,
            "nubank": None,
            "nu bank": None,
            "caixa": None,
            "cef": None,
            "santander": None,
        }
        
        for conn in connectors:
            name_lower = (conn.get('name') or '').lower()
            conn_id = conn.get('id')
            
            # Verificar se é um dos principais bancos
            for keyword in main_banks.keys():
                if keyword in name_lower:
                    if main_banks[keyword] is None:  # Apenas adicionar uma vez
                        main_banks[keyword] = {
                            'id': conn_id,
                            'name': conn.get('name'),
                            'credentials': conn.get('credentials', [])
                        }
                    break
        
        # Exibir bancos encontrados
        for keyword, bank in main_banks.items():
            if bank:
                cred_count = len(bank.get('credentials', []))
                print(f"   ✅ {bank['name']:30} (ID: {bank['id']}, Credenciais: {cred_count})")
        
        # Testar criar um item (conexão) com credenciais fake para ver o comportamento
        print("\n🧪 Testando criação de item (conexão) com credenciais inválidas...")
        print("   ℹ️ Isso vai falhar, mas nos mostrará se a API está respondendo corretamente")
        
        try:
            # Usar o Inter como exemplo (ID geralmente é pequeno)
            inter_connector = None
            for conn in connectors:
                if 'inter' in (conn.get('name') or '').lower() and 'emp' not in (conn.get('name') or '').lower():
                    inter_connector = conn
                    break
            
            if inter_connector:
                print(f"\n   Testando com: {inter_connector['name']} (ID: {inter_connector['id']})")
                
                # Tentar criar conexão com credenciais fake
                fake_creds = {"username": "test@test.com", "password": "testpass"}
                
                try:
                    result = client.create_item(inter_connector['id'], fake_creds)
                    print(f"   📝 Item criado (ou em processamento): {result.get('id')}")
                    print(f"   Status: {result.get('status')}")
                except Exception as e:
                    print(f"   ❌ Erro esperado: {str(e)[:100]}")
            else:
                print("   ⚠️ Inter não encontrado na lista de conectores")
        
        except Exception as e:
            print(f"   ⚠️ Erro ao testar criação de item: {e}")
        
        print("\n" + "="*60)
        print("✅ TESTE CONCLUÍDO COM SUCESSO")
        print("="*60 + "\n")
        print("📝 Próximos passos:")
        print("   1. Verifique se seu banco está na lista acima")
        print("   2. As credenciais devem corresponder aos campos mostrados")
        print("   3. Teste a conexão via Telegram com /conectar_banco")
        print("\n")
        
        return True
        
    except ValueError as e:
        print(f"\n❌ ERRO DE CONFIGURAÇÃO: {e}")
        return False
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_pluggy()
    sys.exit(0 if success else 1)
