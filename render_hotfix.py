#!/usr/bin/env python3
"""
🚀 RENDER HOT FIX - Correções Ultra Robustas
"""

print("🔥 INICIANDO RENDER HOT FIX...")

# FIX 1: PostgreSQL SSL Fix ultra robusto com testing
import os
database_url = os.getenv('DATABASE_URL', '')
if database_url and 'render' in database_url.lower():
    print("🔧 Aplicando SSL Ultra Robusto para PostgreSQL Render...")
    
    # 1. Corrigir protocolo
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    # 2. Garantir SSL requerido
    if 'sslmode=' not in database_url:
        if '?' not in database_url:
            database_url += '?sslmode=require&connect_timeout=10&application_name=maestrofin'
        else:
            database_url += '&sslmode=require&connect_timeout=10&application_name=maestrofin'
    
    os.environ['DATABASE_URL'] = database_url
    print("✅ SSL Ultra Robusto aplicado!")
    
    # 3. Teste de conectividade básico (sem bloquear)
    try:
        print("🔍 Testando conectividade básica PostgreSQL...")
        import psycopg2
        
        # Parse da URL para teste rápido
        from urllib.parse import urlparse
        parsed = urlparse(database_url)
        
        test_conn = psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port,
            database=parsed.path[1:],  # Remove '/' inicial
            user=parsed.username,
            password=parsed.password,
            sslmode='require',
            connect_timeout=5
        )
        
        # Teste rápido
        cursor = test_conn.cursor()
        cursor.execute('SELECT 1')
        result = cursor.fetchone()
        cursor.close()
        test_conn.close()
        
        print("✅ Conectividade PostgreSQL confirmada!")
        
    except ImportError:
        print("⚠️ psycopg2 não disponível para teste (continuando)")
    except Exception as db_test_error:
        print(f"⚠️ Teste de conectividade falhou (continuando): {db_test_error}")
else:
    print("ℹ️ Database URL não configurado ou não é Render")

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
