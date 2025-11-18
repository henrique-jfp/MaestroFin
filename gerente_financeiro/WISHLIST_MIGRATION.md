# 🎯 Migração: Sistema de Metas → Wishlist Inteligente

## 📋 Resumo da Mudança

O antigo sistema de metas (`/novameta`, `/metas`) foi **substituído** pelo novo **Wishlist Inteligente**, que oferece análise de viabilidade financeira e sugestões personalizadas de como atingir seus objetivos.

---

## ✅ O que mudou?

### Comandos Removidos
- ❌ `/novameta` - Criava metas simples

### Comandos Adicionados
- ✅ `/wishlist` - Cria metas com análise completa de viabilidade
- ✅ `/metas` - **MANTIDO** para compatibilidade (agora lista com lógica da wishlist)

---

## 🔄 Compatibilidade com Dados Antigos

### ✅ **Suas metas antigas foram PRESERVADAS!**

O novo sistema usa a **mesma tabela `objetivos`** do banco de dados, então:
- ✅ Todas as metas criadas com `/novameta` continuam visíveis em `/metas`
- ✅ Aportes feitos anteriormente estão salvos
- ✅ Progresso é mantido
- ✅ Histórico preservado

### O que muda na visualização?

Agora ao listar suas metas com `/metas`, você vê:
- 📊 **Análise de prazo**: quantos meses/dias faltam
- 💵 **Quanto economizar/mês**: cálculo automático baseado no prazo
- ⏰ **Alertas inteligentes**: "Prazo próximo!", "Meta atingida!", etc.

---

## 🆕 Como usar a Wishlist

### 1️⃣ Criar nova meta inteligente

```
Usuário: /wishlist
Bot: 💡 Qual é o seu próximo sonho financeiro?

Usuário: Notebook novo
Bot: 💰 Quanto custa: Notebook novo?

Usuário: 4500
Bot: 📅 Em quanto tempo quer conseguir?

Usuário: 6
Bot: 🤖 Analisando sua situação financeira...

Bot: 🎯 Análise: Notebook novo
     💰 Valor: R$ 4.500,00
     📅 Prazo desejado: 6 meses
     
     ━━━━━━━━━━━━━━━━━━━━
     📊 SITUAÇÃO ATUAL
     ━━━━━━━━━━━━━━━━━━━━
     
     💵 Sua poupança média: R$ 350,00/mês
     💡 Você precisa economizar: R$ 750,00/mês
     
     ⚠️ ATENÇÃO: Faltam R$ 400,00/mês para atingir sua meta.
     
     ━━━━━━━━━━━━━━━━━━━━
     💡 COMO VIABILIZAR:
     ━━━━━━━━━━━━━━━━━━━━
     
     Opção 1️⃣: Cortar gastos (redução moderada 30%)
        Reduzindo 30% em 5 categorias
     
     Opção 2️⃣: Cortar gastos (redução agressiva 50%)
        Reduzindo 50% em 5 categorias
     
     Opção 3️⃣: Estender prazo para 11 meses
        Com economia leve (30%), atingível em 11 meses
     
     Escolha uma opção para ver os detalhes:
     [Botões: Opção 1 | Opção 2 | Opção 3 | Cancelar]
```

### 2️⃣ Escolher plano de ação

Ao clicar em uma opção, o bot gera um **plano de ação detalhado**:

```
✅ Meta criada com sucesso!

🎯 Notebook novo
💰 Valor: R$ 4.500,00
📅 Prazo: 6 meses
💵 Economize: R$ 750,00/mês

━━━━━━━━━━━━━━━━━━━━
📋 SEU PLANO DE AÇÃO:
━━━━━━━━━━━━━━━━━━━━

Estratégia: Reduzir gastos em 30%

Onde cortar:
  • Delivery: -R$ 180,00/mês
  • Restaurante: -R$ 120,00/mês
  • Lazer: -R$ 90,00/mês

💰 Total economizado: R$ 390,00/mês

━━━━━━━━━━━━━━━━━━━━
💡 Use /metas para acompanhar seu progresso!
🎮 Cada aporte te dá +25 XP!
```

---

## 🧠 Inteligência da Wishlist

### O que o sistema analisa?

1. **💵 Sua capacidade de poupança**
   - Calcula média dos últimos 3 meses: `(receitas - despesas) / 3`
   
2. **📊 Categorias cortáveis**
   - Identifica gastos não essenciais: Delivery, Restaurante, Lazer, Assinaturas
   - Analisa gastos do mês atual nessas categorias
   - Ordena por potencial de economia

3. **🎯 Viabilidade da meta**
   - Compara: `quanto você precisa economizar/mês` vs `quanto você consegue poupar`
   - Se há déficit, busca opções para viabilizar

4. **💡 Opções de plano**
   - **Cortar 30%**: Redução moderada, mais sustentável
   - **Cortar 50%**: Redução agressiva para metas urgentes
   - **Estender prazo**: Calcula prazo alternativo viável
   - **Aumentar receita**: Mostra quanto de renda extra é necessário

---

## 🔧 Migração Técnica (Para Desenvolvedores)

### Arquivos Removidos
- `gerente_financeiro/metas_handler.py` → renomeado para `.backup`

### Arquivos Adicionados
- `gerente_financeiro/wishlist_handler.py` (598 linhas)

### Mudanças no `bot.py`
```python
# ANTES
from gerente_financeiro.metas_handler import (
    objetivo_conv, listar_metas_command, deletar_meta_callback, edit_meta_conv
)

# DEPOIS
from gerente_financeiro.wishlist_handler import (
    wishlist_conv, listar_wishlist_command, deletar_meta_callback
)
```

### Conversation Handlers
```python
# ANTES
("objetivo_conv", lambda: objetivo_conv),
("edit_meta_conv", lambda: edit_meta_conv),

# DEPOIS
("wishlist_conv", lambda: wishlist_conv),
```

### Command Handlers
```python
# ANTES
("/metas", lambda: CommandHandler("metas", listar_metas_command)),

# DEPOIS (mantém /metas por compatibilidade)
("/metas", lambda: CommandHandler("metas", listar_wishlist_command)),
```

---

## 📊 Estrutura de Dados (Inalterada)

A tabela `objetivos` continua a mesma:

```sql
CREATE TABLE objetivos (
    id SERIAL PRIMARY KEY,
    id_usuario INTEGER REFERENCES usuarios(id),
    descricao VARCHAR(255),
    valor_meta NUMERIC(10, 2),
    valor_atual NUMERIC(10, 2) DEFAULT 0,
    data_meta DATE,
    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Nenhuma migração de banco é necessária!** ✅

---

## 🎮 Gamificação Mantida

- Cada aporte em meta continua dando **+25 XP**
- Conquistas relacionadas a metas são mantidas
- Histórico de aportes preservado

---

## 🆘 Problemas Conhecidos

### 1. Metas antigas sem análise de viabilidade
**Problema**: Metas criadas com `/novameta` não têm análise armazenada  
**Solução**: Use `/wishlist` para criar novas metas com análise, ou continue usando as antigas normalmente

### 2. Edição de metas removida temporariamente
**Problema**: Não há mais `/editarmeta`  
**Solução**: Delete a meta antiga e crie novamente com `/wishlist` (seus aportes podem ser registrados manualmente)

---

## 📞 Suporte

Em caso de dúvidas ou problemas:
- Use `/help` para ver comandos disponíveis
- Reporte bugs no repositório do projeto
- Contate o desenvolvedor: [@seu_usuario]

---

## 🎯 Próximas Features

- [ ] Importar análise de viabilidade para metas antigas
- [ ] Comando `/reavaliar_meta` para recalcular viabilidade
- [ ] Edição de metas com preservação de análise
- [ ] Notificações automáticas quando meta se torna inviável
- [ ] Sugestões proativas: "Vi que você reduziu Delivery! Quer realocar para sua meta?"

---

**Versão**: 3.3.0  
**Data**: 18/11/2025  
**Autor**: Henrique Freitas
