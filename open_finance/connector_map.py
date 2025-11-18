"""
🏦 Mapeamento de Conectores Pluggy
Define quais conectores usar para cada banco
"""

# Mapeamento de conectores preferidos por banco
# Priorizamos aqueles que suportam Open Finance pessoal
BANK_CONNECTOR_MAP = {
    "inter": {
        "preferred_id": 823,  # Inter - CPF only (Open Finance)
        "fallback_ids": [215],  # Inter - sem credenciais (não recomendado)
        "description": "Inter - Open Finance (CPF)"
    },
    "itau": {
        "preferred_id": 601,  # Itaú - CPF only (Open Finance)
        "fallback_ids": [201],  # Itaú - Agência/Conta/Senha (legacy)
        "description": "Itaú - Open Finance (CPF)"
    },
    "bradesco": {
        "preferred_id": 603,  # Bradesco - CPF only (Open Finance)
        "fallback_ids": [203],  # Bradesco - Agência/Conta/Senha/Token (legacy)
        "description": "Bradesco - Open Finance (CPF)"
    },
    "nubank": {
        "preferred_id": 612,  # Nubank - CPF only (Open Finance)
        "fallback_ids": [],
        "description": "Nubank - Open Finance (CPF)"
    },
    "caixa": {
        "preferred_id": 619,  # Caixa - CPF only (Open Finance)
        "fallback_ids": [219, 783],  # Caixa - User/Senha (legacy) ou Caixa Tem
        "description": "Caixa - Open Finance (CPF)"
    },
    "santander": {
        "preferred_id": 608,  # Santander - CPF only (Open Finance)
        "fallback_ids": [208],  # Santander - CPF/Senha (legacy)
        "description": "Santander - Open Finance (CPF)"
    }
}


def get_preferred_connector_id(connector_list: list, bank_keyword: str) -> int:
    """
    Obtém o ID do conector preferido para um banco
    
    Args:
        connector_list: Lista de conectores do Pluggy
        bank_keyword: Palavra-chave do banco (ex: "inter", "itau")
        
    Returns:
        ID do conector preferido
    """
    bank_keyword = bank_keyword.lower().strip()
    
    if bank_keyword not in BANK_CONNECTOR_MAP:
        return None
    
    bank_config = BANK_CONNECTOR_MAP[bank_keyword]
    preferred_id = bank_config["preferred_id"]
    
    # Verificar se o conector preferido está disponível
    for connector in connector_list:
        if connector.get('id') == preferred_id:
            return preferred_id
    
    # Se não encontrar o preferido, tentar os fallbacks
    for fallback_id in bank_config.get("fallback_ids", []):
        for connector in connector_list:
            if connector.get('id') == fallback_id:
                return fallback_id
    
    # Se nenhum foi encontrado, retornar o preferido mesmo assim
    return preferred_id


def filter_and_sort_connectors(connector_list: list) -> list:
    """
    Filtra e ordena os conectores para mostrar apenas os recomendados
    
    Args:
        connector_list: Lista completa de conectores do Pluggy
        
    Returns:
        Lista filtrada e ordenada de conectores recomendados
    """
    blocked_terms = [
        "empresa",
        "empresas",
        "empresarial",
        "business",
        "corporate",
        "pj",
        "bba",
        "pro",
        "emps",
        "corretora",
        "previdência",
        "cartões",
    ]
    
    allowed_keywords = {
        "inter": [215, 823],
        "itaú": [601, 201],
        "itau": [601, 201],
        "bradesco": [203, 603],
        "nubank": [612],
        "nu bank": [612],
        "caixa": [219, 619, 783],
        "cef": [219, 619, 783],
        "santander": [608, 208],
    }
    
    filtered = []
    used_ids = set()
    
    # Primeiro, adicionar os conectores preferidos na ordem desejada
    for bank_name, ids in allowed_keywords.items():
        for target_id in ids:
            for connector in connector_list:
                conn_id = connector.get('id')
                conn_name = (connector.get('name') or '').lower()
                
                if conn_id in used_ids:
                    continue
                
                if conn_id != target_id:
                    continue
                
                # Verificar se está bloqueado
                if any(term in conn_name for term in blocked_terms):
                    continue
                
                filtered.append(connector)
                used_ids.add(conn_id)
                break  # Próximo ID
    
    return filtered


if __name__ == "__main__":
    # Teste
    print("📊 Mapeamento de Conectores Pluggy")
    print("\nBancos mapeados:")
    for bank, config in BANK_CONNECTOR_MAP.items():
        print(f"  ✅ {bank.upper()}: ID {config['preferred_id']} ({config['description']})")
