#!/usr/bin/env python3
"""
🧹 WORKSPACE CLEANER - Limpeza Inteligente do MaestroFin
Remove arquivos obsoletos mantendo funcionalidades essenciais
"""

import os
import shutil
import glob
from pathlib import Path
import sys

class WorkspaceCleaner:
    def __init__(self, workspace_path="."):
        self.workspace_path = Path(workspace_path).resolve()
        self.removed_files = []
        self.removed_dirs = []
        self.errors = []
        
        # ✅ ARQUIVOS ESSENCIAIS - NUNCA REMOVER
        self.essential_files = {
            # Core do sistema
            'bot.py', 'config.py', 'models.py', 'requirements.txt',
            'unified_launcher.py', 'launcher.py', 'jobs.py', 'alerts.py',
            
            # Configurações
            'Procfile', 'nixpacks.toml', 'railway.toml', 'Aptfile',
            '.env', '.gitignore', 'LICENSE',
            
            # README principal
            'README.md',
            
            # Scripts de produção
            'launcher_prod.py', 'launcher_railway.py', 'launcher_simple.py',
            'maestro.sh', 'finalizar_trabalho.sh',
            
            # Base de dados
            'analytics.db',
        }
        
        # ✅ DIRETÓRIOS ESSENCIAIS - NUNCA REMOVER
        self.essential_dirs = {
            'gerente_financeiro', 'database', 'analytics', 'credenciais',
            'static', 'templates', '__pycache__'
        }
        
        # ❌ ARQUIVOS PARA REMOVER (padrões)
        self.removable_patterns = [
            # Documentação desnecessária
            '**/WEBHOOK_*.md', '**/DEBUG_*.md', '**/GUIA_*.md',
            '**/WORKFLOW.md', '**/ARQUIVOS_*.md',
            
            # Launchers obsoletos
            '**/bot_launcher.py', '**/simple_bot_launcher.py',
            '**/bot_render_launcher.py', '**/webhook_launcher.py',
            
            # Configurações antigas
            '**/render.yaml', '**/runtime.txt', '**/advanced_config.py',
            
            # Testes e exemplos
            '**/test_*.py', '**/exemplo_*.py', '**/demo_*.py',
            '**/integration_examples.py', '**/populate_test_data.py',
            
            # Backups e temporários
            '**/*.backup', '**/*.bak', '**/*.tmp', '**/*.temp',
            '**/*_backup.py', '**/*_old.py', '**/*_deprecated.py',
            
            # Logs antigos
            '**/*.log', '**/logs/*.log', '**/dashboard_handler.log',
            
            # Cache e build
            '**/.pytest_cache/**', '**/build/**', '**/dist/**',
            '**/*.egg-info/**',
        ]
        
        # ❌ DIRETÓRIOS PARA REMOVER
        self.removable_dirs = [
            'docs', 'examples', 'tests', 'test',
            '.pytest_cache', 'build', 'dist',
            'backup', 'old', 'deprecated'
        ]

    def is_essential_file(self, file_path):
        """Verifica se é um arquivo essencial"""
        file_name = file_path.name
        return file_name in self.essential_files

    def is_essential_dir(self, dir_path):
        """Verifica se é um diretório essencial"""
        dir_name = dir_path.name
        return dir_name in self.essential_dirs

    def scan_removable_files(self):
        """Escaneia arquivos removíveis baseado nos padrões"""
        removable_files = set()
        
        for pattern in self.removable_patterns:
            for file_path in self.workspace_path.glob(pattern):
                if file_path.is_file() and not self.is_essential_file(file_path):
                    removable_files.add(file_path)
        
        return list(removable_files)

    def scan_removable_dirs(self):
        """Escaneia diretórios removíveis (apenas no workspace raiz)"""
        removable_dirs = []
        
        # Buscar apenas no nível do workspace, ignorar .venv e dependências
        for dir_name in self.removable_dirs:
            workspace_dir = self.workspace_path / dir_name
            if workspace_dir.exists() and workspace_dir.is_dir():
                if not self.is_essential_dir(workspace_dir):
                    removable_dirs.append(workspace_dir)
        
        return removable_dirs

    def remove_file_safe(self, file_path):
        """Remove arquivo de forma segura"""
        try:
            if file_path.exists() and not self.is_essential_file(file_path):
                file_path.unlink()
                self.removed_files.append(str(file_path.relative_to(self.workspace_path)))
                return True
        except Exception as e:
            self.errors.append(f"Erro ao remover {file_path}: {e}")
        return False

    def remove_dir_safe(self, dir_path):
        """Remove diretório de forma segura"""
        try:
            if dir_path.exists() and not self.is_essential_dir(dir_path):
                shutil.rmtree(dir_path)
                self.removed_dirs.append(str(dir_path.relative_to(self.workspace_path)))
                return True
        except Exception as e:
            self.errors.append(f"Erro ao remover diretório {dir_path}: {e}")
        return False

    def clean_pycache(self):
        """Limpa arquivos __pycache__ mas mantém os diretórios"""
        pycache_files = 0
        for pycache_dir in self.workspace_path.glob("**/__pycache__"):
            if pycache_dir.is_dir():
                for pyc_file in pycache_dir.glob("*.pyc"):
                    try:
                        pyc_file.unlink()
                        pycache_files += 1
                    except Exception as e:
                        self.errors.append(f"Erro ao remover {pyc_file}: {e}")
        
        return pycache_files

    def clean_readme_duplicates(self):
        """Remove READMEs duplicados mantendo apenas o principal"""
        readme_files = list(self.workspace_path.glob("**/README.md"))
        main_readme = self.workspace_path / "README.md"
        
        removed_readmes = 0
        for readme in readme_files:
            # Manter apenas o README.md da raiz
            if readme != main_readme and readme.parent != self.workspace_path:
                try:
                    readme.unlink()
                    self.removed_files.append(str(readme.relative_to(self.workspace_path)))
                    removed_readmes += 1
                except Exception as e:
                    self.errors.append(f"Erro ao remover {readme}: {e}")
        
        return removed_readmes

    def show_preview(self):
        """Mostra preview do que será removido"""
        print("🔍 PREVIEW DA LIMPEZA")
        print("=" * 50)
        
        # Escanear arquivos
        removable_files = self.scan_removable_files()
        removable_dirs = self.scan_removable_dirs()
        
        print(f"\n📄 ARQUIVOS A REMOVER ({len(removable_files)}):")
        for file_path in sorted(removable_files):
            print(f"   ❌ {file_path.relative_to(self.workspace_path)}")
        
        print(f"\n📁 DIRETÓRIOS A REMOVER ({len(removable_dirs)}):")
        for dir_path in sorted(removable_dirs):
            print(f"   ❌ {dir_path.relative_to(self.workspace_path)}/")
        
        print(f"\n🗂️ LIMPEZA __pycache__:")
        pycache_count = len(list(self.workspace_path.glob("**/__pycache__/*.pyc")))
        print(f"   🧹 ~{pycache_count} arquivos .pyc")
        
        readme_count = len([r for r in self.workspace_path.glob("**/README.md") 
                           if r != self.workspace_path / "README.md"])
        print(f"\n📖 READMEs DUPLICADOS:")
        print(f"   🧹 ~{readme_count} READMEs secundários")

    def execute_cleaning(self, confirm=True):
        """Executa a limpeza"""
        if confirm:
            print("\n⚠️  CONFIRMAR LIMPEZA?")
            response = input("Digite 'SIM' para continuar: ").strip().upper()
            if response != 'SIM':
                print("❌ Limpeza cancelada.")
                return False
        
        print("\n🧹 INICIANDO LIMPEZA...")
        print("=" * 50)
        
        # 1. Remover arquivos
        removable_files = self.scan_removable_files()
        print(f"\n📄 Removendo {len(removable_files)} arquivos...")
        for file_path in removable_files:
            self.remove_file_safe(file_path)
        
        # 2. Remover diretórios
        removable_dirs = self.scan_removable_dirs()
        print(f"\n📁 Removendo {len(removable_dirs)} diretórios...")
        for dir_path in removable_dirs:
            self.remove_dir_safe(dir_path)
        
        # 3. Limpar __pycache__
        print(f"\n🗂️ Limpando __pycache__...")
        pycache_cleaned = self.clean_pycache()
        
        # 4. Remover READMEs duplicados
        print(f"\n📖 Removendo READMEs duplicados...")
        readme_cleaned = self.clean_readme_duplicates()
        
        return True

    def show_results(self):
        """Mostra resultados da limpeza"""
        print("\n✅ LIMPEZA CONCLUÍDA!")
        print("=" * 50)
        
        print(f"\n📄 ARQUIVOS REMOVIDOS ({len(self.removed_files)}):")
        for file_path in self.removed_files:
            print(f"   ✅ {file_path}")
        
        print(f"\n📁 DIRETÓRIOS REMOVIDOS ({len(self.removed_dirs)}):")
        for dir_path in self.removed_dirs:
            print(f"   ✅ {dir_path}/")
        
        if self.errors:
            print(f"\n❌ ERROS ({len(self.errors)}):")
            for error in self.errors:
                print(f"   ⚠️ {error}")
        
        print(f"\n📊 RESUMO:")
        print(f"   📄 Arquivos: {len(self.removed_files)} removidos")
        print(f"   📁 Diretórios: {len(self.removed_dirs)} removidos")
        print(f"   ❌ Erros: {len(self.errors)}")
        
        if len(self.removed_files) + len(self.removed_dirs) > 0:
            print(f"\n🎯 WORKSPACE LIMPO COM SUCESSO!")
        else:
            print(f"\n🔍 WORKSPACE JÁ ESTAVA LIMPO!")

def main():
    print("🧹 MAESTROFIN WORKSPACE CLEANER")
    print("=" * 50)
    
    # Verificar se está no diretório correto
    current_dir = Path.cwd()
    if not (current_dir / "bot.py").exists():
        print("❌ Execute este script no diretório raiz do MaestroFin!")
        sys.exit(1)
    
    cleaner = WorkspaceCleaner()
    
    # Mostrar preview
    cleaner.show_preview()
    
    # Executar limpeza
    if cleaner.execute_cleaning():
        cleaner.show_results()

if __name__ == "__main__":
    main()
