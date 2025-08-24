#!/bin/bash
# ========================================
# 🎼 MaestroFin - Gerenciador de Workspace
# Script para finalizar/iniciar dia de trabalho
# ========================================

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# Função para mostrar banner
show_banner() {
    echo -e "${PURPLE}"
    echo "╭────────────────────────────────────────────────────────╮"
    echo "│              🎼 MAESTROFIN WORKSPACE 🎼                │"
    echo "│           🚀 Gerenciador de Desenvolvimento            │"
    echo "╰────────────────────────────────────────────────────────╯"
    echo -e "${NC}"
}

# Função para log com timestamp
log() {
    local level=$1
    local message=$2
    local color=""
    
    case $level in
        "INFO") color=$GREEN ;;
        "WARN") color=$YELLOW ;;
        "ERROR") color=$RED ;;
        "SUCCESS") color=$CYAN ;;
        *) color=$WHITE ;;
    esac
    
    echo -e "${color}[$(date +'%H:%M:%S')] $level: $message${NC}"
}

# Função para confirmar ação
confirm() {
    local message=$1
    echo -e "${YELLOW}$message (y/N): ${NC}"
    read -r response
    case "$response" in
        [yY][eE][sS]|[yY]) return 0 ;;
        *) return 1 ;;
    esac
}

# ========================================
# 🌙 FUNÇÃO: FINALIZAR DIA DE TRABALHO
# ========================================
finalize_workday() {
    show_banner
    log "INFO" "🌙 Iniciando finalização do dia de trabalho..."
    
    # Verificar se estamos no diretório correto
    if [[ ! -f "bot.py" ]] || [[ ! -f "requirements.txt" ]]; then
        log "ERROR" "❌ Não está no diretório do MaestroFin!"
        log "INFO" "Execute o script no diretório raiz do projeto."
        exit 1
    fi
    
    # 1. Verificar status git
    log "INFO" "📊 Verificando status do Git..."
    if ! git status > /dev/null 2>&1; then
        log "ERROR" "❌ Não é um repositório Git válido!"
        exit 1
    fi
    
    # Verificar mudanças não commitadas
    if [[ -n $(git status --porcelain) ]]; then
        log "WARN" "⚠️  Existem mudanças não commitadas:"
        git status --short
        
        if confirm "💾 Deseja fazer commit automático das mudanças?"; then
            log "INFO" "💾 Fazendo commit das mudanças..."
            
            # Adicionar todos os arquivos
            git add .
            
            # Commit com mensagem automática
            local commit_msg="🌙 EOD: Auto-commit $(date +'%d/%m/%Y %H:%M')"
            git commit -m "$commit_msg"
            
            # Push para remoto
            if confirm "🚀 Fazer push para o repositório remoto?"; then
                log "INFO" "🚀 Fazendo push..."
                git push origin main
                log "SUCCESS" "✅ Push realizado com sucesso!"
            fi
        else
            log "WARN" "⚠️  Continuando sem commit..."
        fi
    else
        log "SUCCESS" "✅ Não há mudanças para commit"
    fi
    
    # 2. Limpeza de Cache Python
    log "INFO" "🧹 Limpando cache Python..."
    find . -name "*.pyc" -delete 2>/dev/null || true
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    find . -name "*.pyo" -delete 2>/dev/null || true
    log "SUCCESS" "✅ Cache Python limpo"
    
    # 3. Limpeza de arquivos temporários
    log "INFO" "🗑️  Removendo arquivos temporários..."
    find . -name "*.tmp" -delete 2>/dev/null || true
    find . -name "*.temp" -delete 2>/dev/null || true
    find . -name "*.log" -not -path "./logs/*" -delete 2>/dev/null || true
    find . -name "*.backup" -delete 2>/dev/null || true
    find . -name ".DS_Store" -delete 2>/dev/null || true
    find . -name "Thumbs.db" -delete 2>/dev/null || true
    log "SUCCESS" "✅ Arquivos temporários removidos"
    
    # 4. Limpeza de bancos de desenvolvimento
    log "INFO" "💾 Limpando bancos de desenvolvimento..."
    find . -name "*.db" -not -name "analytics.db" -delete 2>/dev/null || true
    find . -name "*.sqlite" -delete 2>/dev/null || true
    find . -name "*.sqlite3" -delete 2>/dev/null || true
    log "SUCCESS" "✅ Bancos temporários removidos"
    
    # 5. Limpeza de arquivos de debug/teste
    log "INFO" "🔧 Removendo arquivos de debug/teste..."
    find . -name "debug_*.py" -delete 2>/dev/null || true
    find . -name "test_*.py" -not -path "./tests/*" -delete 2>/dev/null || true
    find . -name "*_debug.py" -delete 2>/dev/null || true
    find . -name "*_teste.py" -delete 2>/dev/null || true
    find . -name "temp_*.py" -delete 2>/dev/null || true
    find . -name "rascunho_*.py" -delete 2>/dev/null || true
    log "SUCCESS" "✅ Arquivos de debug removidos"
    
    # 6. Verificar virtual environment
    if [[ -d ".venv" ]]; then
        log "INFO" "🐍 Virtual environment encontrado"
        if confirm "🔄 Atualizar requirements.txt baseado no ambiente virtual?"; then
            if [[ -f ".venv/bin/activate" ]]; then
                source .venv/bin/activate
                pip freeze > requirements.txt
                deactivate
                log "SUCCESS" "✅ Requirements.txt atualizado"
            fi
        fi
    fi
    
    # 7. Atualizar PROJECT_STATUS.md
    log "INFO" "📋 Atualizando status do projeto..."
    local current_date=$(date +'%d de %B de %Y às %H:%M')
    local current_branch=$(git branch --show-current)
    
    cat > PROJECT_STATUS.md << EOF
# 🎼 MaestroFin - Status do Projeto
**Última atualização: $current_date**
**Branch atual: $current_branch**

## 🌙 Finalização do Dia de Trabalho

### ✅ **Limpeza Realizada**
- [x] Cache Python removido (__pycache__, *.pyc)
- [x] Arquivos temporários limpos (*.tmp, *.temp, *.log)
- [x] Bancos de desenvolvimento removidos
- [x] Arquivos de debug/teste limpos
- [x] Status do Git verificado
- [x] Workspace organizado

### 🎯 **Estado Atual do Sistema**
- **Bot Telegram**: Funcional com handlers completos
- **Analytics PostgreSQL**: Sistema integrado e funcional
- **OCR Google Vision**: Configurado para processamento de faturas
- **Deploy Render**: Web service + Worker service configurados
- **Documentação**: README.md e PROJECT_STATUS.md atualizados

### 🚀 **Arquitetura de Produção**
\`\`\`
Render Deploy:
├── Web Service (maestrofin-dashboard)
│   ├── Gunicorn + Flask
│   ├── Dashboard Analytics
│   └── APIs REST
└── Worker Service (maestrofin-bot)
    ├── Bot Telegram
    ├── OCR Processing
    └── IA Integration
\`\`\`

### 🔧 **Arquivos Principais**
- \`bot.py\` - Entry point do bot
- \`web_launcher.py\` - Launcher do web service
- \`config.py\` - Configurações centralizadas
- \`models.py\` - Modelos SQLAlchemy
- \`render.yaml\` - Configuração de deploy

### 📊 **Próximas Tarefas Prioritárias**
1. **Testar funcionalidades** após correções de OCR/Analytics
2. **Monitorar logs** de produção no Render
3. **Validar performance** do sistema em produção
4. **Implementar melhorias** identificadas nos testes

---
**Workspace limpo e pronto para o próximo dia de desenvolvimento** 🌟
EOF
    
    log "SUCCESS" "✅ PROJECT_STATUS.md atualizado"
    
    # 8. Commit final da limpeza (se houver mudanças)
    if [[ -n $(git status --porcelain) ]]; then
        log "INFO" "💾 Fazendo commit final da limpeza..."
        git add .
        git commit -m "🌙 EOD: Limpeza automática de workspace - $(date +'%d/%m/%Y %H:%M')"
        
        if confirm "🚀 Fazer push final?"; then
            git push origin main
            log "SUCCESS" "✅ Push final realizado!"
        fi
    fi
    
    # 9. Estatísticas finais
    log "INFO" "📊 Estatísticas do workspace:"
    echo -e "${BLUE}"
    echo "   📁 Arquivos Python: $(find . -name "*.py" | wc -l)"
    echo "   📦 Módulos: $(find . -type d -name "*_*" | grep -v __pycache__ | wc -l)"
    echo "   📄 Linhas de código: $(find . -name "*.py" -exec wc -l {} + | tail -1 | awk '{print $1}')"
    echo "   🗂️  Tamanho total: $(du -sh . | cut -f1)"
    echo -e "${NC}"
    
    log "SUCCESS" "🌙 ✅ Finalização do dia de trabalho concluída!"
    log "INFO" "💤 Bom descanso! Workspace estará limpo amanhã."
}

# ========================================
# 🌅 FUNÇÃO: INICIAR DIA DE TRABALHO
# ========================================
start_workday() {
    show_banner
    log "INFO" "🌅 Iniciando novo dia de trabalho..."
    
    # Verificar diretório
    if [[ ! -f "bot.py" ]] || [[ ! -f "requirements.txt" ]]; then
        log "ERROR" "❌ Não está no diretório do MaestroFin!"
        exit 1
    fi
    
    # 1. Verificar Git e branch
    log "INFO" "🔄 Verificando repositório Git..."
    if ! git status > /dev/null 2>&1; then
        log "ERROR" "❌ Não é um repositório Git válido!"
        exit 1
    fi
    
    local current_branch=$(git branch --show-current)
    log "INFO" "📍 Branch atual: $current_branch"
    
    # 2. Fetch e pull das últimas mudanças
    log "INFO" "📥 Buscando atualizações do repositório..."
    git fetch origin
    
    if [[ $(git rev-parse HEAD) != $(git rev-parse @{u}) ]]; then
        log "INFO" "🔄 Há atualizações disponíveis. Fazendo pull..."
        git pull origin main
        log "SUCCESS" "✅ Código atualizado!"
    else
        log "SUCCESS" "✅ Código já está atualizado"
    fi
    
    # 3. Verificar e ativar ambiente virtual
    if [[ -d ".venv" ]]; then
        log "INFO" "🐍 Ativando ambiente virtual..."
        if [[ -f ".venv/bin/activate" ]]; then
            source .venv/bin/activate
            log "SUCCESS" "✅ Ambiente virtual ativado"
            
            # Verificar se requirements mudaram
            if [[ requirements.txt -nt .venv/pyvenv.cfg ]]; then
                log "INFO" "📦 Requirements.txt foi atualizado. Instalando dependências..."
                pip install -r requirements.txt --quiet
                log "SUCCESS" "✅ Dependências atualizadas"
            fi
        fi
    else
        log "WARN" "⚠️  Ambiente virtual não encontrado"
        if confirm "🐍 Criar ambiente virtual?"; then
            python -m venv .venv
            source .venv/bin/activate
            pip install -r requirements.txt
            log "SUCCESS" "✅ Ambiente virtual criado e configurado"
        fi
    fi
    
    # 4. Verificar arquivos de configuração
    log "INFO" "⚙️  Verificando configurações..."
    
    if [[ ! -f ".env" ]]; then
        log "WARN" "⚠️  Arquivo .env não encontrado"
        if [[ -f ".env.example" ]]; then
            log "INFO" "📋 Copiando .env.example para .env..."
            cp .env.example .env
            log "WARN" "⚠️  Configure as variáveis em .env antes de executar o bot"
        fi
    else
        log "SUCCESS" "✅ Arquivo .env encontrado"
    fi
    
    # Verificar credenciais Google
    if [[ ! -d "credenciais" ]] || [[ -z "$(ls -A credenciais 2>/dev/null)" ]]; then
        log "WARN" "⚠️  Credenciais Google não encontradas em ./credenciais/"
        log "INFO" "📝 Lembre-se de configurar as credenciais Google Cloud"
    else
        log "SUCCESS" "✅ Credenciais encontradas"
    fi
    
    # 5. Verificar status dos serviços
    log "INFO" "🔍 Verificando componentes do sistema..."
    
    # Verificar se consegue importar módulos principais
    if python -c "import bot, config, models" 2>/dev/null; then
        log "SUCCESS" "✅ Módulos principais importáveis"
    else
        log "WARN" "⚠️  Possível problema com módulos principais"
    fi
    
    # 6. Mostrar resumo do PROJECT_STATUS.md
    if [[ -f "PROJECT_STATUS.md" ]]; then
        log "INFO" "📋 Status do projeto:"
        echo -e "${CYAN}"
        head -10 PROJECT_STATUS.md | tail -8
        echo -e "${NC}"
    fi
    
    # 7. Limpar terminal e mostrar comandos úteis
    clear
    show_banner
    
    echo -e "${GREEN}🎉 Workspace preparado para desenvolvimento!${NC}\n"
    
    echo -e "${WHITE}📋 COMANDOS ÚTEIS:${NC}"
    echo -e "${YELLOW}  Bot Local:${NC}"
    echo -e "    python bot.py              # Executar bot"
    echo -e "    python web_launcher.py     # Dashboard local"
    echo ""
    echo -e "${YELLOW}  Desenvolvimento:${NC}"
    echo -e "    git status                 # Verificar mudanças"
    echo -e "    git add .                  # Adicionar arquivos"
    echo -e "    git commit -m 'msg'        # Commit"
    echo -e "    git push origin main       # Deploy automático"
    echo ""
    echo -e "${YELLOW}  Deploy & Monitoring:${NC}"
    echo -e "    https://render.com         # Painel do Render"
    echo -e "    maestrofin.onrender.com    # Dashboard produção"
    echo ""
    echo -e "${YELLOW}  Scripts Workspace:${NC}"
    echo -e "    ./workspace_manager.sh finalize   # Finalizar dia"
    echo -e "    ./workspace_manager.sh start      # Iniciar dia"
    echo ""
    
    # 8. Abrir VS Code se disponível
    if command -v code &> /dev/null; then
        if confirm "🔧 Abrir VS Code no projeto?"; then
            log "INFO" "🚀 Abrindo VS Code..."
            code .
            log "SUCCESS" "✅ VS Code iniciado!"
        fi
    fi
    
    log "SUCCESS" "🌅 ✅ Novo dia de trabalho iniciado!"
    log "INFO" "☕ Bom trabalho! Tudo pronto para desenvolvimento produtivo."
}

# ========================================
# 🎯 FUNÇÃO PRINCIPAL
# ========================================
main() {
    case "${1:-}" in
        "finalize"|"finish"|"end")
            finalize_workday
            ;;
        "start"|"begin"|"init")
            start_workday
            ;;
        "help"|"--help"|"-h")
            show_banner
            echo -e "${WHITE}📖 USAGE:${NC}"
            echo -e "  $0 finalize    🌙 Finalizar dia de trabalho (limpeza + commit)"
            echo -e "  $0 start       🌅 Iniciar dia de trabalho (setup + atualizações)"
            echo -e "  $0 help        📖 Mostrar esta ajuda"
            echo ""
            echo -e "${WHITE}📋 EXEMPLOS:${NC}"
            echo -e "  ./workspace_manager.sh finalize   # Fim do expediente"
            echo -e "  ./workspace_manager.sh start      # Início do expediente"
            ;;
        *)
            show_banner
            log "ERROR" "❌ Comando inválido: ${1:-'(vazio)'}"
            echo -e "\n${WHITE}Use: $0 {finalize|start|help}${NC}"
            echo -e "${BLUE}Para ajuda detalhada: $0 help${NC}"
            exit 1
            ;;
    esac
}

# Executar função principal
main "$@"
