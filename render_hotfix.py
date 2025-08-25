#!/usr/bin/env python3
"""
🚀 RENDER HOT FIX - Correções Ultra Robustas
"""

print("🔥 INICIANDO RENDER HOT FIX...")

# FIX 1: PostgreSQL SSL Fix direto no environment
import os
database_url = os.getenv('DATABASE_URL', '')
if database_url and 'render' in database_url.lower():
    print("🔧 Aplicando SSL Fix para PostgreSQL Render...")
    # Força SSL sem verificação de certificado
    if '?' not in database_url:
        database_url += '?sslmode=require'
    else:
        database_url += '&sslmode=require'
    
    os.environ['DATABASE_URL'] = database_url
    print("✅ SSL Fix aplicado!")

# FIX 2: Setup credenciais Google Vision robustas
print("🔧 Setup Google Vision...")
try:
    # Verificar se credenciais existem
    secret_file = '/etc/secrets/google_vision_credentials.json'
    if os.path.exists(secret_file):
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = secret_file
        print("✅ Google Vision configurado via Secret Files!")
    elif os.getenv('GOOGLE_VISION_CREDENTIALS_JSON'):
        # Criar arquivo temporário
        import tempfile, json
        temp_file = os.path.join(tempfile.gettempdir(), 'google_vision_temp.json')
        with open(temp_file, 'w') as f:
            f.write(os.getenv('GOOGLE_VISION_CREDENTIALS_JSON'))
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = temp_file
        print("✅ Google Vision configurado via Environment Variable!")
    else:
        print("⚠️ Google Vision não configurado (usando fallback)")
except Exception as e:
    print(f"⚠️ Erro configuração Google Vision: {e}")

print("✅ RENDER HOT FIX APLICADO!")
