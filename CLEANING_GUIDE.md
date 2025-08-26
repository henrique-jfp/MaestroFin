# 🧹 Sistema de Limpeza do Workspace

Sistema inteligente para manter o workspace MaestroFin limpo e organizado.

## 🚀 Como Usar

### Opção 1: Menu Interativo (Recomendado)
```bash
./maestro_clean.sh
```

### Opção 2: Limpeza Rápida
```bash
./quick_clean.sh
```

### Opção 3: Limpeza Inteligente
```bash
python3 clean_workspace.py
```

## 🛡️ Segurança

### ✅ **NUNCA Remove**:
- Arquivos essenciais do sistema (`bot.py`, `config.py`, etc.)
- Diretórios funcionais (`gerente_financeiro/`, `database/`, etc.)
- Configurações de produção (`Procfile`, `.env`, etc.)
- README.md principal

### ❌ **Remove Sempre**:
- Documentação obsoleta (`WEBHOOK_*.md`, `DEBUG_*.md`)
- Launchers antigos (`bot_launcher.py`, `simple_bot_launcher.py`)
- Arquivos de teste (`test_*.py`, `exemplo_*.py`)
- Backups e temporários (`*.backup`, `*.tmp`)
- Cache Python (`*.pyc`)

## 📊 Tipos de Limpeza

| Tipo | Tempo | Segurança | Recursos |
|------|-------|-----------|----------|
| **Quick Clean** | ~5s | ✅ Alta | Remoção básica |
| **Smart Clean** | ~10s | ✅ Máxima | Preview + Confirmação |

## 🎯 Exemplo de Uso

```bash
# Ver o que seria removido
./maestro_clean.sh
# Escolher opção 3 (Preview)

# Fazer limpeza completa
./maestro_clean.sh  
# Escolher opção 2 (Smart Clean)

# Commit das mudanças
git add -A && git commit -m "🧹 Workspace cleaned" && git push
```

## ⚠️ Importante

- Execute sempre no diretório raiz do MaestroFin
- O script verifica se `bot.py` existe antes de executar
- Backup automático não é necessário (apenas remove arquivos seguros)
- Logs de remoção são exibidos para auditoria
