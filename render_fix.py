#!/usr/bin/env python3
"""
🚀 RENDER FIX LAUNCHER - Executa correção do analytics no Render
Este script pode ser executado diretamente no Render para corrigir o schema
"""

import os
import sys
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Executa correção do schema analytics"""
    logger.info("🚀 RENDER ANALYTICS FIX - Iniciando...")
    
    # Verificar se está no Render
    is_render = bool(os.environ.get('RENDER_SERVICE_NAME'))
    if not is_render:
        logger.warning("⚠️ Não está executando no Render")
    
    try:
        # Executar correção do schema
        logger.info("🔧 Importando correção do schema...")
        from fix_analytics_schema import fix_analytics_schema, test_new_schema
        
        logger.info("🗑️ Corrigindo schema (drop/recreate)...")
        if fix_analytics_schema():
            logger.info("✅ Schema corrigido!")
            
            logger.info("🧪 Testando novo schema...")
            if test_new_schema():
                logger.info("🎉 SUCESSO! Analytics corrigido no Render!")
                return True
            else:
                logger.error("❌ Teste falhou")
                return False
        else:
            logger.error("❌ Falha na correção")
            return False
            
    except Exception as e:
        logger.error(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
