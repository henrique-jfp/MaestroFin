#!/usr/bin/env python3
"""
TESTE FINAL DO DASHBOARD - SOLUÇÃO DO PROBLEMA
"""

import os
import subprocess
import sys

def main():
    print("🔧 DIAGNÓSTICO E CORREÇÃO DO DASHBOARD")
    print("=" * 50)
    
    # Ir para o diretório correto
    project_dir = "/home/henriquejfp/Área de trabalho/Projetos/Projetos Pessoais/MaestroFin"
    os.chdir(project_dir)
    
    print(f"📁 Diretório atual: {os.getcwd()}")
    
    # Ativar ambiente virtual
    print("🔄 Ativando ambiente virtual...")
    
    # Definir variáveis de ambiente
    env = os.environ.copy()
    env['PYTHONPATH'] = project_dir
    
    try:
        print("🚀 Iniciando dashboard corrigido...")
        print("📊 Acesse: http://localhost:5000")
        print("❤️ Health: http://localhost:5000/health")
        print("💡 Pressione Ctrl+C para parar")
        print("-" * 50)
        
        # Executar dashboard
        result = subprocess.run([
            "/home/henriquejfp/Área de trabalho/Projetos/Projetos Pessoais/MaestroFin/.venv/bin/python",
            "analytics/dashboard_app.py"
        ], env=env)
        
    except KeyboardInterrupt:
        print("\n⏹️ Dashboard parado pelo usuário")
    except Exception as e:
        print(f"❌ Erro: {e}")

if __name__ == "__main__":
    main()
