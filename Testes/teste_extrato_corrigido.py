#!/usr/bin/env python3
"""
Teste básico das funções corrigidas do extrato_handler.py
"""

import sys
import os
sys.path.append('/home/henriquejfp/Projetos Pessoais/MaestroFin/MaestroFin 1.0')

from gerente_financeiro.extrato_handler import (
    ProcessadorDeDocumentos, 
    extrair_transacoes_manualmente,
    categorizar_transacao_automatica,
    normalizar_data,
    extrair_valor_monetario
)

def teste_extracoes():
    """Teste das funções de extração"""
    
    # Teste de extração de valor monetário
    print("=== Teste de Extração de Valores ===")
    valores_teste = [
        "R$ 1.234,56",
        "1.234,56",
        "1234,56", 
        "R$ 50,00",
        "100.000,99"
    ]
    
    for valor_str in valores_teste:
        valor = extrair_valor_monetario(valor_str)
        print(f"'{valor_str}' -> {valor}")
    
    # Teste de normalização de data
    print("\n=== Teste de Normalização de Datas ===")
    datas_teste = [
        "15/01/2024",
        "15-01-2024",
        "2024/01/15",
        "15/1/24"
    ]
    
    for data_str in datas_teste:
        data_norm = normalizar_data(data_str)
        print(f"'{data_str}' -> '{data_norm}'")
    
    # Teste de categorização
    print("\n=== Teste de Categorização ===")
    descricoes_teste = [
        "SUPERMERCADO EXTRA",
        "POSTO SHELL",
        "IFOOD",
        "NETFLIX",
        "FARMACIA DROGASIL",
        "TRANSFERENCIA PIX"
    ]
    
    for desc in descricoes_teste:
        cat, sub = categorizar_transacao_automatica(desc)
        print(f"'{desc}' -> Categoria: {cat}, Subcategoria: {sub}")
    
    print("\n=== Teste de Extração Manual ===")
    texto_extrato_exemplo = """
15 JAN 2024
Transferência enviada pelo Pix João Silva 150,00
Compra no débito via NuPay SUPERMERCADO EXTRA 89,50

16 JAN 2024  
Transferência recebida pelo Pix Maria Santos 200,00
Pagamento de fatura 1.500,00
"""
    
    transacoes = extrair_transacoes_manualmente(texto_extrato_exemplo)
    print(f"Encontradas {len(transacoes)} transações:")
    for t in transacoes:
        print(f"  {t['data']} - {t['descricao']} - R$ {t['valor']:.2f} ({t['tipo_transacao']})")

if __name__ == "__main__":
    teste_extracoes()
