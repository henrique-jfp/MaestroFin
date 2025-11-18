#!/usr/bin/env python3
"""
🧪 Analisar detalhes dos conectores
Mostra informações detalhadas sobre cada conector
"""

import os
import sys
import logging
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Carregar .env
basedir = os.path.abspath(os.path.dirname(__file__))
dotenv_path = os.path.join(basedir, '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)

from open_finance.pluggy_client import PluggyClient

def analyze_connectors():
    """Analisa detalhes dos conectores"""
    
    client = PluggyClient()
    connectors = client.list_connectors(country="BR")
    
    print("\n" + "="*100)
    print("📊 ANÁLISE DETALHADA DE CONECTORES")
    print("="*100 + "\n")
    
    # Filtrar principais bancos
    main_banks = ["inter", "itaú", "itau", "bradesco", "nubank", "caixa", "santander"]
    
    for conn in connectors:
        name = conn.get('name', '')
        name_lower = name.lower()
        
        # Verificar se é um dos principais bancos
        is_main = any(keyword in name_lower for keyword in main_banks)
        
        if is_main and 'emp' not in name_lower:  # Ignorar versões empresariais
            conn_id = conn.get('id')
            credentials = conn.get('credentials', [])
            
            print(f"\n🏦 {name} (ID: {conn_id})")
            print("-" * 100)
            
            # Informações gerais
            print(f"  Status: {conn.get('status', 'N/A')}")
            print(f"  Tipo: {conn.get('type', 'N/A')}")
            
            # Credenciais requeridas
            if credentials:
                print(f"  Credenciais necessárias: {len(credentials)}")
                for i, cred in enumerate(credentials, 1):
                    cred_name = cred.get('name', 'campo')
                    cred_label = cred.get('label', cred_name)
                    cred_type = cred.get('type', 'text')
                    cred_hint = cred.get('hint', '')
                    
                    print(f"    {i}. {cred_label}")
                    print(f"       Nome: {cred_name}")
                    print(f"       Tipo: {cred_type}")
                    if cred_hint:
                        print(f"       Dica: {cred_hint}")
            else:
                print(f"  ⚠️ NENHUMA CREDENCIAL REQUERIDA!")
                print(f"     Isso significa que este conector não precisa de login")
                print(f"     (pode ser uma integração corporativa ou dados públicos)")
            
            # Campos adicionais
            if 'sites' in conn:
                print(f"  Sites: {conn['sites']}")
            if 'portfolio' in conn:
                print(f"  Portfolio: {conn['portfolio']}")

if __name__ == '__main__':
    analyze_connectors()
