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
    Filtra e ordena os conectores para mostrar apenas os recomendados (SEM DUPLICATAS)
    
    Args:
        connector_list: Lista completa de conectores do Pluggy
        
    Returns:
        Lista filtrada e ordenada de conectores recomendados (um por banco)
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
    
    # Ordem de preferência: usar APENAS O PRIMEIRO (preferido) de cada banco
    preferred_connectors = {
        "inter": 823,       # Inter - CPF (Open Finance)
        "itaú": 601,       # Itaú - CPF (Open Finance)
        "itau": 601,       # Itaú - CPF (Open Finance)
        "bradesco": 603,   # Bradesco - CPF (Open Finance)
        "nubank": 612,     # Nubank - CPF (Open Finance)
        "nu bank": 612,    # Nubank alias
        "caixa": 619,      # Caixa - CPF (Open Finance)
        "cef": 619,        # Caixa alias
        "santander": 608,  # Santander - CPF (Open Finance)
    }
    
    filtered = []
    used_bank_names = set()  # Rastrear nomes de banco JÁ ADICIONADOS
    used_connector_ids = set()  # Rastrear IDs já usados
    
    # Adicionar conectores na ordem de preferência
    for bank_keyword, preferred_id in preferred_connectors.items():
        # Ignorar se banco já foi adicionado
        if bank_keyword in used_bank_names:
            continue
        
        # Procurar o conector preferido
        for connector in connector_list:
            conn_id = connector.get('id')
            conn_name = (connector.get('name') or '').lower()
            
            # Verificar se já foi usado
            if conn_id in used_connector_ids:
                continue
            
            # Verificar se é o ID preferido
            if conn_id != preferred_id:
                continue
            
            # Verificar se está bloqueado
            if any(term in conn_name for term in blocked_terms):
                continue
            
            # ✅ Adicionar e marcar como usado
            filtered.append(connector)
            used_connector_ids.add(conn_id)
            used_bank_names.add(bank_keyword)
            break  # Passar para próximo banco
    
    return filtered


if __name__ == "__main__":
    # Teste
    print("📊 Mapeamento de Conectores Pluggy")
    print("\nBancos mapeados:")
    for bank, config in BANK_CONNECTOR_MAP.items():
        print(f"  ✅ {bank.upper()}: ID {config['preferred_id']} ({config['description']})")
