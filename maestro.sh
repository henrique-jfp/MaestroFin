#!/bin/bash
# 🎼 MaestroFin - Script de Controle do Sistema

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Funções de utilidade
print_header() {
    echo -e "${PURPLE}╭─────────────────────────────────────────╮${NC}"
    echo -e "${PURPLE}│  🎼 MAESTROFIN - CONTROLE SISTEMA 🎼   │${NC}"
    echo -e "${PURPLE}╰─────────────────────────────────────────╯${NC}"
    echo ""
}

print_status() {
    local service=$1
    local status=$2
    if [ "$status" = "running" ]; then
        echo -e "   ✅ ${GREEN}$service: ONLINE${NC}"
    else
        echo -e "   ❌ ${RED}$service: OFFLINE${NC}"
    fi
}

# Verificar status dos serviços
check_status() {
    echo -e "${CYAN}📊 STATUS DOS SERVIÇOS:${NC}"
    echo ""
    
    # Bot do Telegram
    if pgrep -f "python.*bot.py" > /dev/null; then
        print_status "Bot Telegram" "running"
        BOT_PID=$(pgrep -f "python.*bot.py")
        echo -e "      PID: $BOT_PID"
    else
        print_status "Bot Telegram" "stopped"
    fi
    
    # Dashboard Analytics
    if pgrep -f "dashboard_app.py" > /dev/null; then
        print_status "Dashboard Analytics" "running"
        DASH_PID=$(pgrep -f "dashboard_app.py")
        echo -e "      PID: $DASH_PID | URL: http://localhost:5001"
    else
        print_status "Dashboard Analytics" "stopped"
    fi
    
    # Sistema completo
    if pgrep -f "start_maestrofin.py\|start_system.py" > /dev/null; then
        print_status "Sistema Completo" "running"
        SYS_PID=$(pgrep -f "start_maestrofin.py\|start_system.py")
        echo -e "      PID: $SYS_PID"
    else
        print_status "Sistema Completo" "stopped"
    fi
    
    # Teste de conectividade
    echo -e "\n${BLUE}🔗 CONECTIVIDADE:${NC}"
    
    # Dashboard local
    echo -n "   📊 Dashboard local: "
    if timeout 3 curl -s -o /dev/null http://localhost:5001 2>/dev/null; then
        echo -e "${GREEN}✅ ACESSÍVEL${NC}"
    else
        echo -e "${RED}❌ INACESSÍVEL${NC}"
    fi
    
    # Dashboard público
    echo -n "   🌐 Dashboard público: "
    if timeout 5 curl -s -o /dev/null http://maestrofin.henriquedejesus.dev 2>/dev/null; then
        echo -e "${GREEN}✅ ACESSÍVEL${NC}"
    else
        echo -e "${RED}❌ INACESSÍVEL${NC}"
    fi
    
    echo ""
}

# Iniciar serviços
start_service() {
    case $1 in
        "bot")
            echo -e "${YELLOW}🤖 Iniciando Bot do Telegram...${NC}"
            if pgrep -f "python.*bot.py" > /dev/null; then
                echo -e "⚠️ ${YELLOW}Bot já está rodando!${NC}"
                return
            fi
            nohup python3 bot.py > bot.log 2>&1 &
            sleep 3
            if pgrep -f "python.*bot.py" > /dev/null; then
                echo -e "✅ ${GREEN}Bot iniciado com sucesso!${NC}"
            else
                echo -e "❌ ${RED}Falha ao iniciar bot${NC}"
            fi
            ;;
        "dashboard")
            echo -e "${YELLOW}🎨 Iniciando Dashboard Analytics...${NC}"
            if pgrep -f "dashboard_app.py" > /dev/null; then
                echo -e "⚠️ ${YELLOW}Dashboard já está rodando!${NC}"
                return
            fi
            nohup python3 analytics/dashboard_app.py > dashboard.log 2>&1 &
            sleep 3
            if pgrep -f "dashboard_app.py" > /dev/null; then
                echo -e "✅ ${GREEN}Dashboard iniciado em http://localhost:5001${NC}"
            else
                echo -e "❌ ${RED}Falha ao iniciar dashboard${NC}"
            fi
            ;;
        "system")
            echo -e "${YELLOW}🚀 Iniciando Sistema Completo...${NC}"
            if pgrep -f "start_maestrofin.py" > /dev/null; then
                echo -e "⚠️ ${YELLOW}Sistema já está rodando!${NC}"
                return
            fi
            nohup python3 start_maestrofin.py > system.log 2>&1 &
            sleep 5
            if pgrep -f "start_maestrofin.py" > /dev/null; then
                echo -e "✅ ${GREEN}Sistema completo iniciado!${NC}"
            else
                echo -e "❌ ${RED}Falha ao iniciar sistema${NC}"
                echo -e "${BLUE}Tentando iniciar componentes separadamente...${NC}"
                start_service "dashboard"
                sleep 2
                start_service "bot"
            fi
            ;;
        "all")
            start_service "dashboard"
            sleep 3
            start_service "bot"
            ;;
    esac
}

# Parar serviços
stop_service() {
    case $1 in
        "bot")
            echo -e "${YELLOW}🛑 Parando Bot do Telegram...${NC}"
            pkill -f "python.*bot.py"
            sleep 1
            if ! pgrep -f "python.*bot.py" > /dev/null; then
                echo -e "✅ ${GREEN}Bot parado${NC}"
            else
                echo -e "⚠️ ${YELLOW}Forçando parada do bot...${NC}"
                pkill -9 -f "python.*bot.py"
            fi
            ;;
        "dashboard")
            echo -e "${YELLOW}🛑 Parando Dashboard...${NC}"
            pkill -f "dashboard_app.py"
            sleep 1
            if ! pgrep -f "dashboard_app.py" > /dev/null; then
                echo -e "✅ ${GREEN}Dashboard parado${NC}"
            else
                echo -e "⚠️ ${YELLOW}Forçando parada do dashboard...${NC}"
                pkill -9 -f "dashboard_app.py"
            fi
            ;;
        "system")
            echo -e "${YELLOW}🛑 Parando Sistema Completo...${NC}"
            pkill -f "start_maestrofin.py"
            pkill -f "start_system.py"
            sleep 1
            echo -e "✅ ${GREEN}Sistema parado${NC}"
            ;;
        "all")
            echo -e "${YELLOW}🛑 Parando todos os serviços...${NC}"
            pkill -f "python.*bot.py"
            pkill -f "dashboard_app.py" 
            pkill -f "start_maestrofin.py"
            pkill -f "start_system.py"
            sleep 2
            echo -e "✅ ${GREEN}Todos os serviços parados${NC}"
            ;;
    esac
}

# Reiniciar serviços
restart_service() {
    echo -e "${YELLOW}🔄 Reiniciando $1...${NC}"
    stop_service $1
    sleep 2
    start_service $1
}

# Ver logs
show_logs() {
    case $1 in
        "bot")
            if [ -f "bot.log" ]; then
                echo -e "${BLUE}📋 Logs do Bot:${NC}"
                tail -20 bot.log
            else
                echo -e "${RED}❌ Log do bot não encontrado${NC}"
            fi
            ;;
        "dashboard")
            if [ -f "dashboard.log" ]; then
                echo -e "${BLUE}📋 Logs do Dashboard:${NC}"
                tail -20 dashboard.log
            else
                echo -e "${RED}❌ Log do dashboard não encontrado${NC}"
            fi
            ;;
        "system")
            if [ -f "system.log" ]; then
                echo -e "${BLUE}📋 Logs do Sistema:${NC}"
                tail -20 system.log
            else
                echo -e "${RED}❌ Log do sistema não encontrado${NC}"
            fi
            ;;
        "all")
            echo -e "${CYAN}📋 Logs disponíveis:${NC}"
            ls -la *.log 2>/dev/null || echo "Nenhum log encontrado"
            ;;
    esac
}

# Menu principal
show_help() {
    echo -e "${BLUE}📋 USO: $0 [COMANDO] [SERVIÇO]${NC}"
    echo ""
    echo -e "${BLUE}COMANDOS:${NC}"
    echo "   start     - Iniciar serviço (padrão: tudo)"
    echo "   stop      - Parar serviço (padrão: tudo)" 
    echo "   restart   - Reiniciar serviço (padrão: tudo)"
    echo "   status, s - Ver status de todos os serviços"
    echo "   logs      - Ver logs"
    echo "   test      - Testar conectividade dos dashboards"
    echo "   ssl       - Configurar certificado SSL"
    echo ""
    echo -e "${BLUE}SERVIÇOS:${NC}"
    echo "   bot       - Bot do Telegram apenas"
    echo "   dashboard - Dashboard Analytics apenas"
    echo "   system    - Sistema completo (start_maestrofin.py)" 
    echo "   all       - Dashboard + Bot separados"
    echo ""
    echo -e "${BLUE}EXEMPLOS:${NC}"
    echo "   $0 start              # Inicia sistema completo (padrão)"
    echo "   $0 start bot          # Inicia apenas o bot"
    echo "   $0 start dashboard    # Inicia apenas o dashboard"
    echo "   $0 stop               # Para tudo"
    echo "   $0 restart            # Reinicia tudo"
    echo "   $0 status             # Ver status de tudo"
    echo "   $0 test               # Testar dashboards"
    echo "   $0 ssl                # Configurar HTTPS"
    echo ""
    echo -e "${GREEN}🎯 COMANDOS PRINCIPAIS:${NC}"
    echo "   $0 start              # ⚡ INICIAR SISTEMA"
    echo "   $0 stop               # 🛑 PARAR SISTEMA"
    echo "   $0 status             # 📊 VER STATUS"
    echo ""
}

# Script principal
main() {
    print_header
    
    case $1 in
        "start")
            if [ -z "$2" ]; then
                echo -e "${BLUE}🚀 Iniciando sistema completo (dashboard + bot)...${NC}"
                start_service "all"
            else
                start_service $2
            fi
            ;;
        "stop")
            if [ -z "$2" ]; then
                stop_service "all"
            else
                stop_service $2
            fi
            ;;
        "restart")
            if [ -z "$2" ]; then
                restart_service "all"
            else
                restart_service $2
            fi
            ;;
        "status"|"s")
            check_status
            ;;
        "logs")
            if [ -z "$2" ]; then
                show_logs "all"
            else
                show_logs $2
            fi
            ;;
        "test")
            echo -e "${BLUE}🧪 Testando conectividade...${NC}"
            echo ""
            
            echo -n "📊 Dashboard local: "
            if timeout 3 curl -s -o /dev/null -w "%{http_code}" http://localhost:5001 2>/dev/null | grep -q "200"; then
                echo -e "${GREEN}✅ OK${NC}"
            else
                echo -e "${RED}❌ FALHOU${NC}"
            fi
            
            echo -n "🌐 Dashboard público: "
            if timeout 5 curl -s -o /dev/null http://maestrofin.henriquedejesus.dev 2>/dev/null; then
                echo -e "${GREEN}✅ OK${NC}"
            else
                echo -e "${RED}❌ FALHOU${NC}"
            fi
            ;;
        "ssl")
            echo -e "${YELLOW}🔐 Configurando SSL para o domínio...${NC}"
            echo "Comando: sudo certbot --nginx -d maestrofin.henriquedejesus.dev"
            read -p "Executar? (s/n): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Ss]$ ]]; then
                sudo certbot --nginx -d maestrofin.henriquedejesus.dev
            fi
            ;;
        *)
            show_help
            ;;
    esac
}

# Executar função principal
main "$@"
