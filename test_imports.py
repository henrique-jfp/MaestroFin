#!/usr/bin/env python3
"""
Teste para verificar qual import pode estar travando o bot
"""

import sys
import traceback

def test_import(module_name, description):
    try:
        print(f"🔄 Testando: {description}")
        if module_name == "config":
            import config
        elif module_name == "database":
            from database.database import get_db, popular_dados_iniciais, criar_tabelas
        elif module_name == "models":
            import models
        elif module_name == "dashboard_handler":
            from gerente_financeiro.dashboard_handler import cmd_dashboard, cmd_dashstatus, dashboard_callback_handler
        elif module_name == "handlers":
            from gerente_financeiro.handlers import create_gerente_conversation_handler
        elif module_name == "agendamentos":
            from gerente_financeiro.agendamentos_handler import agendamento_start, agendamento_conv
        elif module_name == "metas":
            from gerente_financeiro.metas_handler import objetivo_conv, listar_metas_command
        elif module_name == "fatura":
            from gerente_financeiro.fatura_handler import fatura_conv, callback_agendar_parcelas_sim
        elif module_name == "telegram":
            from telegram.ext import Application, CommandHandler, ApplicationBuilder
        elif module_name == "genai":
            import google.generativeai as genai
        elif module_name == "database_operations":
            from database.database import get_db, popular_dados_iniciais, criar_tabelas
            criar_tabelas()
            db = next(get_db())
            popular_dados_iniciais(db)
            db.close()
        
        print(f"✅ {description} - OK")
        return True
    except Exception as e:
        print(f"❌ {description} - ERRO:")
        print(f"   Tipo: {type(e).__name__}")
        print(f"   Mensagem: {str(e)}")
        print(f"   Traceback: {traceback.format_exc()}")
        return False

def main():
    print("🔍 Testando importações e inicializações do bot...\n")
    
    tests = [
        ("config", "Configurações"),
        ("telegram", "Telegram Bot API"),
        ("genai", "Google Generative AI"),
        ("models", "Modelos do banco de dados"),
        ("database", "Database imports"),
        ("database_operations", "Database operations (criar_tabelas, popular_dados)"),
        ("handlers", "Handlers básicos"),
        ("dashboard_handler", "Dashboard handler"),
        ("agendamentos", "Agendamentos handler"),
        ("metas", "Metas handler"),
        ("fatura", "Fatura handler"),
    ]
    
    results = []
    for module, desc in tests:
        result = test_import(module, desc)
        results.append((desc, result))
        print()
    
    print("📊 RESULTADOS:")
    for desc, result in results:
        status = "✅ OK" if result else "❌ ERRO"
        print(f"   {status} {desc}")
    
    failed_count = sum(1 for _, result in results if not result)
    if failed_count == 0:
        print("\n🎉 Todos os testes passaram! O problema pode estar na execução do bot.")
    else:
        print(f"\n⚠️ {failed_count} teste(s) falharam.")

if __name__ == "__main__":
    main()
