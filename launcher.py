#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚀 MaestroFin Launcher
Script para iniciar bot + dashboard simultaneamente
"""

import os
import sys
import time
import signal
import subprocess
import threading
from pathlib import Path

def banner():
    """Exibe banner do sistema"""
    print("=" * 60)
    print("🌟 MAESTROFIN - SISTEMA FINANCEIRO COMPLETO")
    print("=" * 60)
    print("📱 Bot Telegram + 🌐 Dashboard Web")
    print("🚀 Iniciando todos os serviços...")
    print("=" * 60)

def verificar_dependencias():
    """Verifica se todas as dependências estão instaladas"""
    try:
        import flask
        import plotly
        import pandas
        import telegram
        print("✅ Todas as dependências encontradas")
        return True
    except ImportError as e:
        print(f"❌ Dependência não encontrada: {e}")
        print("💡 Execute: pip install -r requirements.txt")
        return False

def iniciar_dashboard():
    """Inicia o dashboard em thread separada"""
    print("🌐 Iniciando Dashboard Web...")
    
    # Verificar se porta 5000 está livre
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('localhost', 5000))
    sock.close()
    
    if result == 0:
        print("⚠️ Porta 5000 já está em uso, tentando usar dashboard existente...")
        try:
            import requests
            response = requests.get("http://localhost:5000/api/status", timeout=5)
            if response.status_code == 200:
                print("✅ Dashboard já está rodando!")
                print("🔗 Acesse: http://localhost:5000")
                print("📊 Demo: http://localhost:5000/dashboard/demo")
                return "EXISTING"  # Sinalizar que já existe
        except:
            print("❌ Porta ocupada por outro serviço")
            return None
    
    try:
        # Usar dashboard principal
        dashboard_cmd = [sys.executable, "dashboard_app.py"]
        
        processo_dashboard = subprocess.Popen(
            dashboard_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Aguardar o dashboard inicializar
        time.sleep(5)
        
        # Verificar se o processo ainda está rodando
        if processo_dashboard.poll() is None:
            print("✅ Dashboard iniciado com sucesso!")
            print("🔗 Acesse: http://localhost:5000")
            print("📊 Demo: http://localhost:5000/dashboard/demo")
            return processo_dashboard
        else:
            stdout, stderr = processo_dashboard.communicate()
            print(f"❌ Erro ao iniciar dashboard:")
            if stdout:
                print(f"STDOUT: {stdout}")
            if stderr:
                print(f"STDERR: {stderr}")
            return None
            
    except Exception as e:
        print(f"❌ Erro ao iniciar dashboard: {e}")
        return None

def iniciar_bot():
    """Inicia o bot com melhor tratamento de erros"""
    print("🤖 Iniciando Bot Telegram...")
    
    tentativas = 0
    max_tentativas = 3
    
    while tentativas < max_tentativas:
        try:
            # Comando para iniciar o bot
            bot_cmd = [sys.executable, "bot.py"]
            
            # Configurar ambiente para suprimir warnings
            env = os.environ.copy()
            env['PYTHONWARNINGS'] = 'ignore'
            
            processo_bot = subprocess.Popen(
                bot_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
                preexec_fn=os.setsid  # Criar novo grupo de processo
            )
            
            # Aguardar um pouco para verificar se o bot iniciou
            time.sleep(10)  # Tempo maior para estabilizar
            
            # Verificar se o processo ainda está rodando
            if processo_bot.poll() is None:
                print("✅ Bot iniciado com sucesso!")
                return processo_bot
            else:
                stdout, stderr = processo_bot.communicate()
                print(f"❌ Bot falhou (tentativa {tentativas + 1}):")
                if stdout:
                    print(f"STDOUT: {stdout[:500]}...")
                if stderr:
                    print(f"STDERR: {stderr[:500]}...")
                    
                # Se é erro de rede, tentar novamente após delay
                if "network" in stderr.lower() or "timeout" in stderr.lower():
                    tentativas += 1
                    print(f"🔄 Tentando novamente em 30 segundos...")
                    time.sleep(30)
                    continue
                # Se é apenas warning, não considerar como erro fatal
                elif "warning" in stderr.lower() and "error" not in stderr.lower() and "exception" not in stderr.lower():
                    print("⚠️  Bot iniciou com warnings, mas está funcionando")
                    return processo_bot
                else:
                    print("❌ Erro não é de rede, parando tentativas")
                    break
                    
        except Exception as e:
            print(f"❌ Erro ao iniciar bot: {e}")
            tentativas += 1
            if tentativas < max_tentativas:
                print(f"🔄 Tentando novamente em 30 segundos...")
                time.sleep(30)
    
    print(f"❌ Falha ao iniciar bot após {max_tentativas} tentativas")
    return None

def monitorar_processos(processos):
    """Monitora os processos - SEM restart automático para evitar loops"""
    print("👀 Monitorando processos...")
    print("💡 Pressione Ctrl+C para parar todos os serviços")
    
    tentativas_restart = {}
    max_tentativas = 2
    
    try:
        while True:
            for nome, processo in list(processos.items()):
                if processo and processo != "EXISTING" and hasattr(processo, 'poll') and processo.poll() is not None:
                    print(f"⚠️ {nome} parou inesperadamente!")
                    
                    # Contar tentativas de restart
                    if nome not in tentativas_restart:
                        tentativas_restart[nome] = 0
                    
                    tentativas_restart[nome] += 1
                    
                    if tentativas_restart[nome] <= max_tentativas:
                        print(f"🔄 Tentativa {tentativas_restart[nome]} de reiniciar {nome}...")
                        
                        if nome == "Dashboard":
                            novo_processo = iniciar_dashboard()
                            if novo_processo and novo_processo != "EXISTING":
                                processos[nome] = novo_processo
                                print(f"✅ {nome} reiniciado com sucesso!")
                            else:
                                print(f"❌ Falha ao reiniciar {nome}")
                                del processos[nome]
                        elif nome == "Bot":
                            novo_processo = iniciar_bot()
                            if novo_processo:
                                processos[nome] = novo_processo
                                print(f"✅ {nome} reiniciado com sucesso!")
                            else:
                                print(f"❌ Falha ao reiniciar {nome}")
                                del processos[nome]
                    else:
                        print(f"❌ {nome} falhou {max_tentativas} vezes. Removendo do monitoramento.")
                        del processos[nome]
            
            # Se não sobrou nenhum processo, encerrar
            if not processos:
                print("❌ Todos os processos falharam. Encerrando sistema.")
                break
            
            time.sleep(10)  # Verificar a cada 10 segundos
            
    except KeyboardInterrupt:
        print("🛑 Parando todos os serviços...")
        
        for nome, processo in processos.items():
            if processo and processo != "EXISTING" and hasattr(processo, 'poll') and processo.poll() is None:
                print(f"⏹️ Parando {nome}...")
                try:
                    if hasattr(processo, 'pid'):
                        os.killpg(os.getpgid(processo.pid), signal.SIGTERM)
                    else:
                        processo.terminate()
                    
                    # Aguardar término gracioso
                    try:
                        processo.wait(timeout=3)
                        print(f"✅ {nome} parado com sucesso")
                    except (subprocess.TimeoutExpired, KeyboardInterrupt):
                        print(f"🔥 Forçando parada do {nome}...")
                        if hasattr(processo, 'pid'):
                            try:
                                os.killpg(os.getpgid(processo.pid), signal.SIGKILL)
                            except:
                                processo.kill()
                        else:
                            processo.kill()
                except Exception as e:
                    print(f"⚠️ Erro ao parar {nome}: {e}")
        
        print("✅ Todos os serviços foram parados")

def main():
    """Função principal"""
    banner()
    
    # Verificar dependências
    if not verificar_dependencias():
        return 1
    
    # Verificar se estamos no diretório correto
    if not Path("bot.py").exists():
        print("❌ Arquivo bot.py não encontrado!")
        print("💡 Execute este script no diretório do MaestroFin")
        return 1
    
    processos = {}
    
    # Iniciar dashboard
    resultado_dashboard = iniciar_dashboard()
    if resultado_dashboard == "EXISTING":
        print("📊 Dashboard já está em execução")
        processos["Dashboard"] = "EXISTING"
    elif resultado_dashboard:
        processos["Dashboard"] = resultado_dashboard
    else:
        print("❌ Falha ao iniciar dashboard - continuando só com bot")
    
    # Iniciar bot
    processo_bot = iniciar_bot()
    if processo_bot:
        processos["Bot"] = processo_bot
    else:
        print("❌ Falha ao iniciar bot")
        if processos.get("Dashboard") and processos["Dashboard"] != "EXISTING":
            processos["Dashboard"].terminate()
        return 1
    
    # Verificar se pelo menos um serviço está rodando
    if not processos:
        print("❌ Nenhum serviço foi iniciado com sucesso!")
        return 1
    
    print(f"🎉 {len(processos)} serviço(s) iniciado(s) com sucesso!")
    print("📋 RESUMO DOS SERVIÇOS:")

    if "Dashboard" in processos:
        print("🌐 Dashboard Web: http://localhost:5000")
        print("📊 Demo Dashboard: http://localhost:5000/dashboard/demo")
    
    if "Bot" in processos:
        print("📱 Bot Telegram: Ativo e respondendo")
    
    # Monitorar processos
    monitorar_processos(processos)
    
    return 0

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except Exception as e:
        print(f"💥 Erro crítico: {e}")
        sys.exit(1)

import subprocess
import sys
import time
import signal
import os
from threading import Thread
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MaestroFinLauncher:
    """Gerenciador para executar bot e dashboard"""
    
    def __init__(self):
        self.bot_process = None
        self.dashboard_process = None
        self.running = False
    
    def start_bot(self):
        """Inicia o bot do Telegram"""
        try:
            logger.info("🤖 Iniciando bot do Telegram...")
            self.bot_process = subprocess.Popen([
                sys.executable, "bot.py"
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            # Monitor de saída do bot
            def monitor_bot():
                for line in iter(self.bot_process.stdout.readline, ''):
                    if line.strip():
                        logger.info(f"[BOT] {line.strip()}")
                
                for line in iter(self.bot_process.stderr.readline, ''):
                    if line.strip():
                        logger.error(f"[BOT ERROR] {line.strip()}")
            
            Thread(target=monitor_bot, daemon=True).start()
            logger.info("✅ Bot iniciado com sucesso!")
            
        except Exception as e:
            logger.error(f"❌ Erro ao iniciar bot: {e}")
    
    def start_dashboard(self):
        """Inicia o dashboard web"""
        try:
            logger.info("🌐 Iniciando dashboard web...")
            
            # Aguardar um pouco para o bot inicializar
            time.sleep(3)
            
            self.dashboard_process = subprocess.Popen([
                sys.executable, "dashboard_app.py"
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            # Monitor de saída do dashboard
            def monitor_dashboard():
                for line in iter(self.dashboard_process.stdout.readline, ''):
                    if line.strip():
                        logger.info(f"[DASHBOARD] {line.strip()}")
                
                for line in iter(self.dashboard_process.stderr.readline, ''):
                    if line.strip():
                        logger.error(f"[DASHBOARD ERROR] {line.strip()}")
            
            Thread(target=monitor_dashboard, daemon=True).start()
            logger.info("✅ Dashboard iniciado com sucesso!")
            
        except Exception as e:
            logger.error(f"❌ Erro ao iniciar dashboard: {e}")
    
    def stop_all(self):
        """Para todos os processos"""
        logger.info("🛑 Parando todos os serviços...")
        
        self.running = False
        
        if self.bot_process:
            try:
                self.bot_process.terminate()
                self.bot_process.wait(timeout=10)
                logger.info("✅ Bot parado")
            except Exception as e:
                logger.error(f"❌ Erro ao parar bot: {e}")
                if self.bot_process:
                    self.bot_process.kill()
        
        if self.dashboard_process:
            try:
                self.dashboard_process.terminate()
                self.dashboard_process.wait(timeout=10)
                logger.info("✅ Dashboard parado")
            except Exception as e:
                logger.error(f"❌ Erro ao parar dashboard: {e}")
                if self.dashboard_process:
                    self.dashboard_process.kill()
    
    def check_health(self):
        """Verifica saúde dos processos"""
        bot_status = "✅ Ativo" if self.bot_process and self.bot_process.poll() is None else "❌ Inativo"
        dashboard_status = "✅ Ativo" if self.dashboard_process and self.dashboard_process.poll() is None else "❌ Inativo"
        
        return {
            'bot': bot_status,
            'dashboard': dashboard_status
        }
    
    def run(self):
        """Executa ambos os serviços"""
        logger.info("🎼 MAESTROFIN - Iniciando sistema completo...")
        logger.info("=" * 50)
        
        try:
            self.running = True
            
            # Iniciar bot
            self.start_bot()
            
            # Iniciar dashboard
            self.start_dashboard()
            
            # Status inicial
            logger.info("📊 Status dos serviços:")
            status = self.check_health()
            for service, status_text in status.items():
                logger.info(f"  {service.upper()}: {status_text}")
            
            logger.info("=" * 50)
            logger.info("🎯 Sistema iniciado! Pressione Ctrl+C para parar")
            logger.info("🌐 Dashboard: http://localhost:5000")
            logger.info("🤖 Bot: Ativo no Telegram")
            logger.info("=" * 50)
            
            # Loop principal - verificar processos
            while self.running:
                time.sleep(30)  # Verificar a cada 30 segundos
                
                # Verificar se processos ainda estão ativos
                if self.bot_process and self.bot_process.poll() is not None:
                    logger.warning("⚠️ Bot parou inesperadamente, reiniciando...")
                    self.start_bot()
                
                if self.dashboard_process and self.dashboard_process.poll() is not None:
                    logger.warning("⚠️ Dashboard parou inesperadamente, reiniciando...")
                    self.start_dashboard()
        
        except KeyboardInterrupt:
            logger.info("🛑 Interrupção solicitada pelo usuário")
        except Exception as e:
            logger.error(f"❌ Erro durante execução: {e}")
        finally:
            self.stop_all()
            logger.info("👋 MaestroFin finalizado")

def signal_handler(signum, frame):
    """Handler para sinais do sistema"""
    logger.info(f"📡 Sinal recebido: {signum}")
    sys.exit(0)

def main():
    """Função principal"""
    # Verificar se estamos no diretório correto
    if not os.path.exists("bot.py") or not os.path.exists("dashboard_app.py"):
        logger.error("❌ Arquivos bot.py ou dashboard_app.py não encontrados!")
        logger.error("💡 Execute este script no diretório raiz do MaestroFin")
        sys.exit(1)
    
    # Configurar handlers de sinal
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Verificar argumentos da linha de comando
    if len(sys.argv) > 1:
        if sys.argv[1] == "--bot-only":
            logger.info("🤖 Executando apenas o bot...")
            subprocess.run([sys.executable, "bot.py"])
            return
        elif sys.argv[1] == "--dashboard-only":
            logger.info("🌐 Executando apenas o dashboard...")
            subprocess.run([sys.executable, "dashboard_app.py"])
            return
        elif sys.argv[1] == "--help":
            print("""
🎼 MaestroFin Launcher

Uso:
  python launcher.py                 # Executa bot + dashboard
  python launcher.py --bot-only      # Executa apenas o bot
  python launcher.py --dashboard-only # Executa apenas o dashboard
  python launcher.py --help          # Mostra esta ajuda

Portas:
  Dashboard: http://localhost:5000
  Bot: Conecta ao Telegram via API

Requisitos:
  - Arquivo .env configurado
  - Dependências instaladas (requirements.txt)
  - Python 3.12+
""")
            return
    
    # Executar launcher completo
    launcher = MaestroFinLauncher()
    launcher.run()

if __name__ == "__main__":
    main()
