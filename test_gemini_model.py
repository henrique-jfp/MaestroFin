#!/usr/bin/env python3
"""
Script de teste para verificar modelo Gemini configurado
"""

import os
import sys

# Adiciona o diretório do projeto ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config

print("=" * 60)
print("🔍 VERIFICAÇÃO DE CONFIGURAÇÃO DO MODELO GEMINI")
print("=" * 60)

print(f"\n📋 Variável de ambiente GEMINI_MODEL_NAME:")
env_value = os.getenv("GEMINI_MODEL_NAME")
print(f"   Valor bruto: {env_value if env_value else '❌ NÃO DEFINIDO'}")

print(f"\n🤖 Modelo carregado pelo config.py:")
print(f"   {config.GEMINI_MODEL_NAME}")

print(f"\n✅ Modelos válidos disponíveis:")
for modelo in config.VALID_GEMINI_MODELS:
    status = "✅" if modelo == config.GEMINI_MODEL_NAME else "  "
    print(f"   {status} {modelo}")

print("\n" + "=" * 60)

# Testar conexão com API
try:
    import google.generativeai as genai
    
    genai.configure(api_key=config.GEMINI_API_KEY)
    
    print("\n🔬 TESTANDO MODELO...")
    model = genai.GenerativeModel(config.GEMINI_MODEL_NAME)
    
    # Teste simples
    response = model.generate_content("Responda apenas 'OK' se você está funcionando.")
    print(f"✅ Modelo '{config.GEMINI_MODEL_NAME}' funcionando!")
    print(f"   Resposta: {response.text}")
    
except Exception as e:
    print(f"❌ ERRO ao testar modelo: {e}")
    print("\n⚠️ SUGESTÃO: Atualize a variável de ambiente no Railway:")
    print(f"   GEMINI_MODEL_NAME=gemini-1.5-flash")

print("\n" + "=" * 60)
