# 🎼 MaestroFin - Gerenciamento de Workspace

## 🎯 **Scripts de Produtividade**

Este projeto inclui scripts automatizados para gerenciar o ciclo de desenvolvimento diário de forma eficiente e organizada.

## 📋 **Scripts Disponíveis**

### 🌙 **Finalizar Dia de Trabalho**
```bash
# Opções disponíveis:
./workspace_manager.sh finalize
./end_day.sh                    # Atalho rápido

# O que faz:
✅ Verifica status do Git e faz commit automático
✅ Limpa cache Python (__pycache__, *.pyc)
✅ Remove arquivos temporários (*.tmp, *.log, *.backup)
✅ Limpa bancos de desenvolvimento
✅ Remove arquivos de debug/teste
✅ Atualiza requirements.txt se necessário
✅ Atualiza PROJECT_STATUS.md com timestamp
✅ Faz commit final da limpeza
✅ Push automático (opcional)
✅ Mostra estatísticas do projeto
```

### 🌅 **Iniciar Dia de Trabalho**
```bash
# Opções disponíveis:
./workspace_manager.sh start
./start_day.sh                  # Atalho rápido

# O que faz:
✅ Verifica e atualiza repositório (git pull)
✅ Ativa ambiente virtual Python
✅ Atualiza dependências se necessário
✅ Verifica arquivos de configuração (.env)
✅ Valida credenciais Google Cloud
✅ Testa imports dos módulos principais
✅ Mostra status atual do projeto
✅ Limpa terminal e exibe comandos úteis
✅ Abre VS Code (opcional)
```

## 🚀 **Como Usar**

### **Fim do Expediente** 🌙
```bash
cd /path/to/MaestroFin
./end_day.sh

# Ou usar o completo:
./workspace_manager.sh finalize
```

### **Início do Expediente** 🌅
```bash
cd /path/to/MaestroFin
./start_day.sh

# Ou usar o completo:
./workspace_manager.sh start
```

### **Ajuda e Documentação** 📖
```bash
./workspace_manager.sh help
```

## 🔧 **VS Code Integration**

O projeto inclui configuração completa para VS Code:

### **Tasks Disponíveis** (Ctrl+Shift+P > "Tasks: Run Task")
- 🤖 **Executar Bot Local** - Roda `python bot.py`
- 🌐 **Executar Dashboard Local** - Roda `python web_launcher.py`
- 🧹 **Finalizar Dia de Trabalho** - Executa limpeza automática
- 🌅 **Iniciar Dia de Trabalho** - Setup do ambiente
- 📦 **Instalar Dependências** - `pip install -r requirements.txt`
- 🚀 **Deploy (Git Push)** - Push automático para deploy

### **Debug Configurations**
- 🤖 **Debug Bot** - Debug do bot com breakpoints
- 🌐 **Debug Dashboard** - Debug do dashboard web

## 📂 **Arquivos do Sistema**

| Arquivo | Descrição |
|---------|-----------|
| `workspace_manager.sh` | Script principal de gerenciamento |
| `end_day.sh` | Atalho para finalizar dia |
| `start_day.sh` | Atalho para iniciar dia |
| `MaestroFin.code-workspace` | Configuração VS Code |
| `PROJECT_STATUS.md` | Status atualizado automaticamente |

## 🎨 **Personalização**

### **Adicionar Ações Customizadas**
Edite `workspace_manager.sh` nas funções:
- `finalize_workday()` - Para ações de fim de dia
- `start_workday()` - Para ações de início de dia

### **Configurar Atalhos VS Code**
Adicione keybindings em VS Code:
```json
{
    "key": "ctrl+shift+e",
    "command": "workbench.action.tasks.runTask",
    "args": "🧹 Finalizar Dia de Trabalho"
},
{
    "key": "ctrl+shift+s",  
    "command": "workbench.action.tasks.runTask",
    "args": "🌅 Iniciar Dia de Trabalho"
}
```

## ⚡ **Workflow Recomendado**

### **Início do Dia** 🌅
1. Chegar no trabalho
2. `./start_day.sh`
3. Verificar PROJECT_STATUS.md
4. Começar desenvolvimento

### **Durante o Desenvolvimento** 💻
- Use tasks do VS Code para executar bot/dashboard
- Use debug configurations para debugging
- Commits regulares conforme desenvolve

### **Fim do Dia** 🌙
1. Finalizar funcionalidades
2. `./end_day.sh`
3. Confirmar push automático
4. Workspace limpo para amanhã

## 🎯 **Benefícios**

✅ **Workspace sempre limpo** - Remove clutter automaticamente  
✅ **Código sempre atualizado** - Pull automático no início do dia  
✅ **Commits organizados** - Commits automáticos no fim do dia  
✅ **Ambiente consistente** - Setup automático de venv e dependências  
✅ **Produtividade máxima** - Foco no desenvolvimento, não na configuração  
✅ **Documentação atualizada** - PROJECT_STATUS.md sempre atual  
✅ **Deploy automático** - Push para main = deploy no Render  

---

**🎼 MaestroFin - Desenvolvimento organizado e produtivo!** 🚀
