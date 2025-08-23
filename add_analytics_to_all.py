#!/usr/bin/env python3
"""
🚀 Script para adicionar tracking de analytics em TODOS os handlers
"""

import os
import re

# Definir handlers importantes para tracking
HANDLERS_TO_TRACK = {
    'graficos.py': ['chart_callback_handler'],
    'dashboard_handler.py': ['dashboard_callback_handler'],  
    'delete_user_handler.py': ['start_delete_flow'],
    'editing_handler.py': ['start_editing'],
    'fatura_handler.py': ['start_fatura_flow', 'handle_fatura_photo'],
    'extrato_handler.py': ['start_extrato_flow'],
    'metas_handler.py': ['start_meta_flow', 'edit_meta_flow'],
    'relatorio_handler.py': ['start_relatorio_flow'],
    'contact_handler.py': ['start_contact_flow']
}

ANALYTICS_IMPORT = '''# Importar analytics
try:
    from analytics.bot_analytics import BotAnalytics
    from analytics.advanced_analytics import advanced_analytics
    analytics = BotAnalytics()
    ANALYTICS_ENABLED = True
except ImportError:
    ANALYTICS_ENABLED = False

def track_analytics(command_name):
    """Decorator para tracking de comandos"""
    import functools
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(update, context):
            if ANALYTICS_ENABLED and update.effective_user:
                user_id = update.effective_user.id
                username = update.effective_user.username or update.effective_user.first_name or "Usuário"
                
                try:
                    analytics.track_command_usage(
                        user_id=user_id,
                        username=username,
                        command=command_name,
                        success=True
                    )
                    logging.info(f"📊 Analytics: {username} usou /{command_name}")
                except Exception as e:
                    logging.error(f"❌ Erro no analytics: {e}")
            
            return await func(update, context)
        return wrapper
    return decorator

'''

def add_analytics_to_file(file_path, handlers):
    """Adiciona analytics a um arquivo"""
    print(f"🔧 Processando {file_path}...")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Verificar se já tem analytics
    if 'track_analytics' in content:
        print(f"✅ {file_path} já tem analytics")
        return
    
    # Adicionar import no início (após imports padrão)
    import_pattern = r'(import logging.*?\n)'
    if re.search(import_pattern, content):
        content = re.sub(import_pattern, f'{ANALYTICS_IMPORT}\\1', content)
    
    # Adicionar decorators nas funções
    for handler in handlers:
        # Encontrar a função e adicionar decorator
        pattern = f'(async def {handler}\\(.*?\\):)'
        if re.search(pattern, content):
            command_name = handler.replace('start_', '').replace('_handler', '').replace('_flow', '').replace('_callback', '')
            decorator = f'@track_analytics("{command_name}")\n'
            content = re.sub(pattern, f'{decorator}\\1', content)
            print(f"✅ Adicionado tracking para {handler} -> {command_name}")
    
    # Salvar arquivo
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

def main():
    print("🚀 Adicionando analytics a todos os handlers...")
    
    base_path = '/home/henriquejfp/Área de trabalho/Projetos/Projetos Pessoais/MaestroFin/gerente_financeiro'
    
    for filename, handlers in HANDLERS_TO_TRACK.items():
        file_path = os.path.join(base_path, filename)
        if os.path.exists(file_path):
            add_analytics_to_file(file_path, handlers)
        else:
            print(f"⚠️ Arquivo não encontrado: {filename}")
    
    print("\n🎉 Analytics adicionado a todos os handlers!")

if __name__ == "__main__":
    main()
