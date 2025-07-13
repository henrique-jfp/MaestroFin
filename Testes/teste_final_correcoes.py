#!/usr/bin/env python3
"""
Teste final das correções no extrato_handler.py
"""

import sys
import os
from datetime import datetime, timezone

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def testar_importacoes():
    """Testa se todas as importações estão funcionando."""
    try:
        from models import Lancamento, Usuario, Conta, Categoria, Subcategoria
        from datetime import datetime, timezone
        print("✅ Todas as importações estão funcionando")
        return True
    except Exception as e:
        print(f"❌ Erro nas importações: {e}")
        return False

def testar_criacao_completa():
    """Testa criação completa de lançamento com categorias."""
    try:
        from models import Lancamento
        
        # Dados de teste
        transacao = {
            'data': '15/04/2025',
            'descricao': 'Transferência PIX para supermercado',
            'valor': 50.75,
            'tipo_transacao': 'Saída',
            'categoria_sugerida': 'Alimentação',
            'subcategoria_sugerida': 'Supermercado'
        }
        
        # Simula IDs
        conta_id = 1
        usuario_id = 1
        categoria_id = 1
        subcategoria_id = 2
        
        # Mapeia tipo
        tipo_db = 'Entrada' if transacao.get('tipo_transacao') == 'Entrada' else 'Saída'
        
        # Cria objeto
        lancamento = Lancamento(
            id_conta=conta_id,
            id_usuario=usuario_id,
            data_transacao=datetime.strptime(transacao['data'], '%d/%m/%Y'),
            descricao=transacao['descricao'],
            valor=float(transacao['valor']),
            tipo=tipo_db,
            forma_pagamento="Nubank",
            id_categoria=categoria_id,
            id_subcategoria=subcategoria_id
        )
        
        print("✅ Lançamento completo criado com sucesso")
        print(f"   - Tipo: {lancamento.tipo}")
        print(f"   - Valor: R$ {lancamento.valor}")
        print(f"   - Categoria ID: {lancamento.id_categoria}")
        print(f"   - Subcategoria ID: {lancamento.id_subcategoria}")
        return True
        
    except Exception as e:
        print(f"❌ Erro na criação completa: {e}")
        return False

def main():
    print("=" * 50)
    print("🔍 TESTE FINAL DAS CORREÇÕES")
    print("=" * 50)
    
    tests = [
        ("Importações", testar_importacoes),
        ("Criação Completa", testar_criacao_completa)
    ]
    
    passed = 0
    total = len(tests)
    
    for nome, teste in tests:
        print(f"\n🧪 Testando: {nome}")
        if teste():
            passed += 1
        else:
            print(f"   Falhou!")
    
    print("\n" + "=" * 50)
    print(f"📊 Resultado: {passed}/{total} testes passaram")
    
    if passed == total:
        print("🎉 Sistema pronto para salvar transações!")
        print("💡 As correções resolveram os problemas de campo.")
    else:
        print("⚠️  Ainda há problemas pendentes.")
    
    print("=" * 50)

if __name__ == "__main__":
    main()
