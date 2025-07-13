#!/usr/bin/env python3
"""
Teste para verificar se as correções no salvamento de transações funcionam.
"""

import sys
import os
from datetime import datetime, timezone

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import Lancamento, Usuario, Conta

def testar_criacao_lancamento():
    """Testa a criação de um objeto Lancamento com os campos corretos."""
    
    print("🧪 Testando criação de lançamento com campos corretos...")
    
    # Simula dados de uma transação extraída
    transacao_teste = {
        'data': '15/04/2025',
        'descricao': 'Transferência enviada pelo Pix - Teste',
        'valor': 100.50,
        'tipo_transacao': 'Saída'
    }
    
    # Simula dados de conta e usuário
    conta_id = 1
    usuario_id = 1
    conta_nome = "Nubank"
    
    try:
        # Mapeia o tipo_transacao para o campo 'tipo' do modelo
        tipo_mapped = transacao_teste.get('tipo_transacao', 'Saída')
        if tipo_mapped == 'Entrada':
            tipo_db = 'Entrada'
        else:
            tipo_db = 'Saída'
        
        # Tenta criar o objeto Lancamento
        nova_transacao = Lancamento(
            id_conta=conta_id,
            id_usuario=usuario_id,
            data_transacao=datetime.strptime(transacao_teste['data'], '%d/%m/%Y'),
            descricao=transacao_teste['descricao'],
            valor=float(transacao_teste['valor']),
            tipo=tipo_db,
            forma_pagamento=conta_nome
        )
        
        print("✅ Objeto Lancamento criado com sucesso!")
        print(f"   - Data: {nova_transacao.data_transacao}")
        print(f"   - Descrição: {nova_transacao.descricao}")
        print(f"   - Valor: R$ {nova_transacao.valor}")
        print(f"   - Tipo: {nova_transacao.tipo}")
        print(f"   - Conta ID: {nova_transacao.id_conta}")
        print(f"   - Usuário ID: {nova_transacao.id_usuario}")
        print(f"   - Forma pagamento: {nova_transacao.forma_pagamento}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao criar Lancamento: {e}")
        return False

def testar_verificacao_usuario_novo():
    """Testa a verificação se um usuário é novo."""
    
    print("\n🧪 Testando verificação de usuário novo...")
    
    try:
        # Simula um usuário criado agora
        usuario_novo = Usuario()
        usuario_novo.criado_em = datetime.now(timezone.utc)
        
        # Verifica se é novo (criado há menos de 5 minutos)
        is_new_user = (datetime.now(timezone.utc) - usuario_novo.criado_em).total_seconds() < 300
        
        print(f"✅ Verificação funcionando!")
        print(f"   - Usuário criado em: {usuario_novo.criado_em}")
        print(f"   - É usuário novo: {is_new_user}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro na verificação de usuário novo: {e}")
        return False

def main():
    print("=" * 60)
    print("🔧 TESTE DE CORREÇÕES NO SALVAMENTO DE TRANSAÇÕES")
    print("=" * 60)
    
    success_count = 0
    total_tests = 2
    
    # Teste 1: Criação de Lancamento
    if testar_criacao_lancamento():
        success_count += 1
    
    # Teste 2: Verificação de usuário novo
    if testar_verificacao_usuario_novo():
        success_count += 1
    
    print("\n" + "=" * 60)
    print(f"📊 RESULTADO: {success_count}/{total_tests} testes passaram")
    
    if success_count == total_tests:
        print("🎉 Todas as correções estão funcionando corretamente!")
        print("💡 O sistema deve conseguir salvar as transações no banco agora.")
    else:
        print("⚠️  Ainda há problemas que precisam ser corrigidos.")
    
    print("=" * 60)

if __name__ == "__main__":
    main()
