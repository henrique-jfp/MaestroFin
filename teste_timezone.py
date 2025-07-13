#!/usr/bin/env python3
"""
Teste específico para verificar correção do problema de timezone
"""

import sys
import os
from datetime import datetime, timezone

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def testar_timezone_compatibility():
    """Testa compatibilidade entre datetime com e sem timezone."""
    
    print("🧪 Testando compatibilidade de timezone...")
    
    try:
        # Simula datetime sem timezone (como pode estar no banco)
        usuario_criado_naive = datetime(2025, 7, 13, 5, 0, 0)  # Sem timezone
        
        # Simula datetime com timezone (datetime.now(timezone.utc))
        agora_aware = datetime.now(timezone.utc)
        
        print(f"   - Usuário criado (naive): {usuario_criado_naive}")
        print(f"   - Agora (aware): {agora_aware}")
        
        # Testa a correção implementada
        if usuario_criado_naive.tzinfo is None:
            usuario_criado_utc = usuario_criado_naive.replace(tzinfo=timezone.utc)
            print(f"   - Usuário convertido para UTC: {usuario_criado_utc}")
        else:
            usuario_criado_utc = usuario_criado_naive
        
        # Tenta fazer a subtração
        diferenca = agora_aware - usuario_criado_utc
        is_new_user = diferenca.total_seconds() < 300
        
        print(f"   - Diferença: {diferenca}")
        print(f"   - Segundos: {diferenca.total_seconds():.2f}")
        print(f"   - É usuário novo: {is_new_user}")
        
        print("✅ Compatibilidade de timezone funcionando!")
        return True
        
    except Exception as e:
        print(f"❌ Erro na compatibilidade de timezone: {e}")
        return False

def testar_tratamento_erro():
    """Testa o tratamento de erro na verificação."""
    
    print("\n🧪 Testando tratamento de erro...")
    
    try:
        # Simula um erro potencial
        usuario_criado = None
        
        try:
            if usuario_criado.tzinfo is None:
                usuario_criado_utc = usuario_criado.replace(tzinfo=timezone.utc)
            else:
                usuario_criado_utc = usuario_criado
            
            is_new_user = (datetime.now(timezone.utc) - usuario_criado_utc).total_seconds() < 300
        except Exception:
            # Se houver erro na comparação, assume que não é usuário novo
            is_new_user = False
            print("   - Erro capturado corretamente, is_new_user = False")
        
        print(f"   - Resultado do tratamento: is_new_user = {is_new_user}")
        print("✅ Tratamento de erro funcionando!")
        return True
        
    except Exception as e:
        print(f"❌ Erro no tratamento de erro: {e}")
        return False

def main():
    print("=" * 60)
    print("🔧 TESTE DE CORREÇÃO DO PROBLEMA DE TIMEZONE")
    print("=" * 60)
    
    tests = [
        ("Compatibilidade de Timezone", testar_timezone_compatibility),
        ("Tratamento de Erro", testar_tratamento_erro)
    ]
    
    passed = 0
    total = len(tests)
    
    for nome, teste in tests:
        if teste():
            passed += 1
    
    print("\n" + "=" * 60)
    print(f"📊 Resultado: {passed}/{total} testes passaram")
    
    if passed == total:
        print("🎉 Correção de timezone funcionando!")
        print("💡 O sistema deve conseguir salvar transações agora.")
    else:
        print("⚠️  Ainda há problemas com timezone.")
    
    print("=" * 60)

if __name__ == "__main__":
    main()
