#!/usr/bin/env python3
"""
🔧 RENDER COMPATIBILITY - render_launcher.py
Arquivo de compatibilidade para resolver problemas de deploy.
Redireciona para o unified_launcher.py correto.
"""

import os
import sys
import logging

# Configurar logging básico
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Função principal de compatibilidade"""
    logger.info("⚠️  RENDER_LAUNCHER COMPATIBILITY MODE")
    logger.info("📍 Redirecionando para unified_launcher.py...")

    try:
        # Adicionar diretório atual ao path se necessário
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
        
        # Importar e executar o unified_launcher
        import unified_launcher
        
        logger.info("✅ unified_launcher.py carregado via compatibilidade")
        
        # Executar o main do unified launcher
        unified_launcher.main()
        
    except ImportError as e:
        logger.error(f"❌ Erro ao importar unified_launcher: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Erro na execução: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()