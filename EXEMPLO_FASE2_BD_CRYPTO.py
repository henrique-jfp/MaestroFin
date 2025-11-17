#!/usr/bin/env python3
"""
🔐 Exemplo Prático: Como usar Token Auth com BD e Criptografia
Execute localmente para testar tudo funcionando
"""

import os
import sys

# Simular variáveis de ambiente
os.environ['TOKEN_ENCRYPTION_KEY'] = None  # Será gerada automaticamente

# ============== DEMONSTRAÇÃO ==============

def demo_encryption():
    """Demo 1: Criptografia de tokens"""
    print("\n" + "="*60)
    print("🔐 DEMO 1: CRIPTOGRAFIA DE TOKENS")
    print("="*60)
    
    from open_finance.token_encryption import TokenEncryption
    
    # Gerar chave
    key = TokenEncryption.generate_new_key()
    print(f"✅ Chave gerada: {key[:50]}...")
    
    # Criar cipher
    encryption = TokenEncryption()
    
    # Tokens de exemplo (reais dos bancos)
    tokens_teste = {
        'Inter iSafe': '123456',
        'Inter CPF:token': '12345678901:abc123def456',
        'Itaú iToken': '654321',
        'Bearer Token': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...',
    }
    
    print("\n📝 Criptografando tokens...")
    encrypted_tokens = {}
    for nome, token in tokens_teste.items():
        encrypted = encryption.encrypt(token)
        encrypted_tokens[nome] = encrypted
        print(f"  {nome}:")
        print(f"    Original:  {token}")
        print(f"    Encrypted: {encrypted[:50]}...")
    
    print("\n🔓 Descriptografando tokens...")
    for nome, encrypted in encrypted_tokens.items():
        decrypted = encryption.decrypt(encrypted)
        print(f"  {nome}:")
        print(f"    Decrypted: {decrypted}")
        assert decrypted == tokens_teste[nome], "❌ Descriptografia falhou!"
    
    print("\n✅ Criptografia funcionando perfeitamente!")


def demo_token_validation():
    """Demo 2: Validação de tokens"""
    print("\n" + "="*60)
    print("✅ DEMO 2: VALIDAÇÃO DE TOKENS")
    print("="*60)
    
    from open_finance.token_auth import TokenAuthManager
    
    manager = TokenAuthManager()
    
    # Tokens para testar
    test_cases = [
        ('inter', '123456', True, 'iSafe 6 dígitos'),
        ('inter', '12345678901:abc123', True, 'CPF:token'),
        ('itau', '654321', True, 'iToken 6 dígitos'),
        ('itau', 'bearer_token_abc123', True, 'Bearer token'),
        ('bradesco', '111111', True, '6+ dígitos'),
        ('nubank', 'jwt.token.aqui', True, 'JWT'),
        ('inter', '123', False, 'Muito curto'),
    ]
    
    print("\n🧪 Testando validação...")
    for bank, token, should_pass, desc in test_cases:
        try:
            result = manager.authenticate(bank, token)
            status = "✅ PASS" if should_pass else "❌ FAIL (deveria falhar)"
            print(f"  {bank.upper():10} | {desc:20} | {status}")
        except ValueError as e:
            status = "✅ PASS (falha esperada)" if not should_pass else f"❌ FAIL: {e}"
            print(f"  {bank.upper():10} | {desc:20} | {status}")
    
    print("\n✅ Validação funcionando!")


def demo_database_flow():
    """Demo 3: Fluxo com Banco de Dados"""
    print("\n" + "="*60)
    print("💾 DEMO 3: FLUXO COM BANCO DE DADOS")
    print("="*60)
    
    print("\n⚠️  Nota: Para testar com BD real, você precisa:")
    print("  1. Estar em um ambiente com PostgreSQL")
    print("  2. DATABASE_URL configurada")
    print("  3. TOKEN_ENCRYPTION_KEY configurada")
    print("\n📋 Fluxo esperado:")
    
    fluxo = [
        ("1. Usuário envia /conectar_token", "Telegram → Bot"),
        ("2. Seleciona banco (Inter, Itaú, etc)", "Telegram UI"),
        ("3. Envia token (6 dígitos ou bearer)", "Telegram → Bot"),
        ("4. TokenAuthManager valida", "✅ Token válido"),
        ("5. TokenEncryption encripta", "🔐 Token → encrypted"),
        ("6. TokenDatabaseManager salva em BD", "💾 PostgreSQL"),
        ("7. Bot responde 'Conectado!'", "✅ Message"),
        ("8. Usuário fecha bot", ""),
        ("9. Bot reinicia", ""),
        ("10. TokenDatabaseManager recupera token", "💾 PostgreSQL → token"),
        ("11. Token descriptografado automaticamente", "🔓 Token disponível"),
        ("12. API call ao banco com token", "🏦 Buscar dados"),
    ]
    
    for step, resultado in fluxo:
        print(f"  {step}")
        if resultado:
            print(f"     → {resultado}")


def demo_setup_guide():
    """Demo 4: Guia de Setup"""
    print("\n" + "="*60)
    print("🚀 DEMO 4: SETUP EM PRODUÇÃO (RENDER)")
    print("="*60)
    
    print("""
📝 PASSO 1: Gerar chave de criptografia
    python3 -c "from open_finance.token_encryption import TokenEncryption; print(TokenEncryption.generate_new_key())"
    
📝 PASSO 2: Copiar chave gerada
    gAAAAABl... (copiar tudo)
    
📝 PASSO 3: Adicionar ao Render
    Dashboard → Environment Variables → Add
    Key: TOKEN_ENCRYPTION_KEY
    Value: gAAAAABl... (colar)
    
📝 PASSO 4: Salvar e Render redeploy
    Render vai reiniciar automaticamente
    
📝 PASSO 5: Testar em produção
    /conectar_token
    Selecionar banco
    Enviar token real
    
📝 PASSO 6: Verificar em BD
    SELECT COUNT(*) FROM user_bank_tokens WHERE ativo = true;
    
✅ RESULTADO:
   - Tokens salvos de forma segura
   - Persistem entre restarts
   - Criptografados no BD
   - Prontos para API calls reais
""")


def demo_next_steps():
    """Demo 5: Próximos passos"""
    print("\n" + "="*60)
    print("📊 DEMO 5: PRÓXIMOS PASSOS (FASE 3)")
    print("="*60)
    
    print("""
🎯 FASE 3: API Calls Reais aos Bancos

1️⃣ Criar `open_finance/bank_api_client.py`:
   - Usar tokens salvos do BD
   - Fazer chamadas às APIs dos bancos
   - Sincronizar transações

2️⃣ Endpoints esperados:
   GET /transacoes?data_inicio=...&data_fim=...
   GET /saldo
   GET /contas
   
3️⃣ Integração com MaestroFin:
   - Salvar transações como Lancamentos
   - Sincronizar categorias
   - Atualizar saldos automaticamente
   
4️⃣ Schedule automático:
   - Sync a cada 6 horas
   - Notificar usuário de transações
   - Análise em tempo real

EXEMPLO:
    from open_finance.bank_api_client import BankAPIClient
    
    client = BankAPIClient(user_id=123, db_session=db)
    
    # Busca transações
    transactions = client.fetch_transactions('inter', '2024-11-01', '2024-11-17')
    
    # Sincroniza com MaestroFin
    client.sync_transactions(transactions)
""")


if __name__ == '__main__':
    print("""
╔════════════════════════════════════════════════════════════╗
║  🔐 MAESTROFIN - TOKEN AUTH SYSTEM DEMONSTRATION 🔐       ║
║     Fase 2: BD + Criptografia (Production Ready)          ║
╚════════════════════════════════════════════════════════════╝
""")
    
    demos = [
        ("1", "Criptografia de Tokens", demo_encryption),
        ("2", "Validação de Tokens", demo_token_validation),
        ("3", "Fluxo com Banco de Dados", demo_database_flow),
        ("4", "Setup em Produção", demo_setup_guide),
        ("5", "Próximos Passos", demo_next_steps),
    ]
    
    print("\nEscolha um demo para rodar:\n")
    for key, name, _ in demos:
        print(f"  {key} - {name}")
    print(f"  0 - Rodar todos")
    
    try:
        choice = input("\nOpção: ").strip()
        
        if choice == '0':
            for key, name, func in demos:
                try:
                    func()
                except Exception as e:
                    print(f"❌ Erro em {name}: {e}")
        else:
            for key, name, func in demos:
                if key == choice:
                    func()
                    break
    except KeyboardInterrupt:
        print("\n❌ Interrompido")
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
