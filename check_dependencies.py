#!/usr/bin/env python3
"""
🔍 VERIFICADOR DE DEPENDÊNCIAS
Testa se todos os imports do projeto podem ser resolvidos.
Executa ANTES do deploy para detectar módulos faltando no requirements.txt
"""

import ast
import sys
from pathlib import Path
from collections import defaultdict

# Módulos que são built-in do Python (não vão estar no requirements.txt)
STDLIB_MODULES = {
    'abc', 'aifc', 'argparse', 'array', 'ast', 'asynchat', 'asyncio', 'asyncore',
    'atexit', 'audioop', 'base64', 'bdb', 'binascii', 'binhex', 'bisect', 'builtins',
    'bz2', 'calendar', 'cgi', 'cgitb', 'chunk', 'cmath', 'cmd', 'code', 'codecs',
    'codeop', 'collections', 'colorsys', 'compileall', 'concurrent', 'configparser',
    'contextlib', 'contextvars', 'copy', 'copyreg', 'cProfile', 'crypt', 'csv',
    'ctypes', 'curses', 'dataclasses', 'datetime', 'dbm', 'decimal', 'difflib',
    'dis', 'distutils', 'doctest', 'dummy_threading', 'email', 'encodings', 'enum',
    'errno', 'faulthandler', 'fcntl', 'filecmp', 'fileinput', 'fnmatch', 'formatter',
    'fractions', 'ftplib', 'functools', 'gc', 'getopt', 'getpass', 'gettext', 'glob',
    'grp', 'gzip', 'hashlib', 'heapq', 'hmac', 'html', 'http', 'imaplib', 'imghdr',
    'imp', 'importlib', 'inspect', 'io', 'ipaddress', 'itertools', 'json', 'keyword',
    'lib2to3', 'linecache', 'locale', 'logging', 'lzma', 'mailbox', 'mailcap',
    'marshal', 'math', 'mimetypes', 'mmap', 'modulefinder', 'msilib', 'msvcrt',
    'multiprocessing', 'netrc', 'nis', 'nntplib', 'numbers', 'operator', 'optparse',
    'os', 'ossaudiodev', 'parser', 'pathlib', 'pdb', 'pickle', 'pickletools', 'pipes',
    'pkgutil', 'platform', 'plistlib', 'poplib', 'posix', 'posixpath', 'pprint',
    'profile', 'pstats', 'pty', 'pwd', 'py_compile', 'pyclbr', 'pydoc', 'queue',
    'quopri', 'random', 're', 'readline', 'reprlib', 'resource', 'rlcompleter',
    'runpy', 'sched', 'secrets', 'select', 'selectors', 'shelve', 'shlex', 'shutil',
    'signal', 'site', 'smtpd', 'smtplib', 'sndhdr', 'socket', 'socketserver',
    'spwd', 'sqlite3', 'ssl', 'stat', 'statistics', 'string', 'stringprep', 'struct',
    'subprocess', 'sunau', 'symbol', 'symtable', 'sys', 'sysconfig', 'syslog',
    'tabnanny', 'tarfile', 'telnetlib', 'tempfile', 'termios', 'test', 'textwrap',
    'threading', 'time', 'timeit', 'tkinter', 'token', 'tokenize', 'trace',
    'traceback', 'tracemalloc', 'tty', 'turtle', 'turtledemo', 'types', 'typing',
    'typing_extensions', 'unicodedata', 'unittest', 'urllib', 'uu', 'uuid', 'venv',
    'warnings', 'wave', 'weakref', 'webbrowser', 'winreg', 'winsound', 'wsgiref',
    'xdrlib', 'xml', 'xmlrpc', 'zipapp', 'zipfile', 'zipimport', 'zlib',
    '__future__', '__main__'
}

def extract_imports_from_file(filepath):
    """Extrai todos os imports de um arquivo Python"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read(), filename=str(filepath))
        
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    # Pega só o top-level module
                    imports.add(alias.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module.split('.')[0])
        
        return imports
    except SyntaxError as e:
        print(f"  ⚠️ Erro de sintaxe em {filepath}: {e}")
        return set()
    except Exception as e:
        print(f"  ⚠️ Erro ao processar {filepath}: {e}")
        return set()

def scan_project():
    """Escaneia todos os arquivos .py do projeto"""
    project_root = Path(__file__).parent
    all_imports = defaultdict(list)
    
    print(f"🔍 Escaneando projeto em: {project_root}")
    print("=" * 70)
    
    # Busca todos os .py exceto os de teste e cache
    py_files = [
        f for f in project_root.rglob("*.py")
        if '__pycache__' not in str(f) 
        and 'test_' not in f.name
        and '.venv' not in str(f)
        and 'venv' not in str(f)
    ]
    
    print(f"📦 {len(py_files)} arquivos Python encontrados\n")
    
    for filepath in py_files:
        imports = extract_imports_from_file(filepath)
        for imp in imports:
            all_imports[imp].append(filepath.relative_to(project_root))
    
    return all_imports

def check_requirements():
    """Verifica se requirements.txt está em sincronia com os imports"""
    requirements_path = Path(__file__).parent / 'requirements.txt'
    
    if not requirements_path.exists():
        print("❌ requirements.txt não encontrado!")
        return set()
    
    installed_packages = set()
    with open(requirements_path, 'r') as f:
        for line in f:
            line = line.strip()
            # Ignora comentários e linhas vazias
            if line and not line.startswith('#'):
                # Pega só o nome do pacote (antes de == ou >=)
                pkg_name = line.split('==')[0].split('>=')[0].split('<')[0].strip()
                # Alguns pacotes têm nomes diferentes no import vs pip
                pkg_name = pkg_name.lower().replace('-', '_')
                installed_packages.add(pkg_name)
    
    return installed_packages

def main():
    print("🎼 MaestroFin - Verificador de Dependências")
    print("=" * 70)
    print()
    
    # 1. Escaneia todos os imports
    all_imports = scan_project()
    
    # 2. Lê o requirements.txt
    installed = check_requirements()
    
    # Mapeamento de nomes diferentes entre import e pip
    PACKAGE_MAPPING = {
        'PIL': 'pillow',
        'cv2': 'opencv_python_headless',
        'fitz': 'pymupdf',
        'google': 'google_generativeai',  # pode ser vários pacotes google-*
        'telegram': 'python_telegram_bot',
        'dateutil': 'python_dateutil',
        'dotenv': 'python_dotenv',
    }
    
    # 3. Filtra imports internos e stdlib
    internal_modules = {'gerente_financeiro', 'analytics', 'database', 'legacy'}
    
    external_imports = {}
    for module, files in all_imports.items():
        if module in STDLIB_MODULES or module in internal_modules:
            continue
        external_imports[module] = files
    
    # 4. Verifica quais estão faltando
    missing = []
    for module in sorted(external_imports.keys()):
        # Normaliza o nome para comparar
        check_name = PACKAGE_MAPPING.get(module, module).lower().replace('-', '_')
        
        # Verifica se está no requirements
        found = any(check_name in pkg for pkg in installed)
        
        if not found:
            missing.append(module)
    
    # 5. Relatório
    print("\n📊 RELATÓRIO DE DEPENDÊNCIAS")
    print("=" * 70)
    
    if missing:
        print(f"\n❌ {len(missing)} MÓDULOS FALTANDO NO requirements.txt:")
        print("-" * 70)
        for module in missing:
            files_using = external_imports[module][:3]  # Mostra até 3 arquivos
            print(f"\n  • {module}")
            print(f"    Usado em: {', '.join(str(f) for f in files_using)}")
            if len(external_imports[module]) > 3:
                print(f"    ... e mais {len(external_imports[module]) - 3} arquivos")
    else:
        print("\n✅ TUDO OK! Todos os módulos externos estão no requirements.txt")
    
    print("\n" + "=" * 70)
    print(f"Total de módulos externos: {len(external_imports)}")
    print(f"Total de módulos OK: {len(external_imports) - len(missing)}")
    print(f"Total de módulos faltando: {len(missing)}")
    print("=" * 70)
    
    return len(missing)

if __name__ == "__main__":
    exit_code = main()
    sys.exit(0 if exit_code == 0 else 1)
