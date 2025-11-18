# 🐛 BUGFIX: Compras no Cartão Classificadas como "Receita"

**Data:** 18/11/2025  
**Commit:** 9263c39  
**Severidade:** 🔴 **CRÍTICA** (afeta todas as importações de cartão de crédito)

---

## 📋 Descrição do Bug

Todas as **compras no cartão de crédito** estavam sendo incorretamente classificadas como **"Receita (ganho)"** ao invés de **"Despesa (gasto)"**.

### Exemplo do Problema:

```
❌ ANTES DO FIX:
- Compra A FORMIGUINHA R$ 12,00 → tipo: "Receita" (ERRADO!)
- Compra D COPA PANIFICACAO R$ 6,00 → tipo: "Receita" (ERRADO!)
- Compra MERCATO EXPRESS R$ 67,59 → tipo: "Receita" (ERRADO!)

✅ DEPOIS DO FIX:
- Compra A FORMIGUINHA R$ 12,00 → tipo: "Despesa" (CORRETO!)
- Compra D COPA PANIFICACAO R$ 6,00 → tipo: "Despesa" (CORRETO!)
- Compra MERCATO EXPRESS R$ 67,59 → tipo: "Despesa" (CORRETO!)
```

---

## 🔍 Causa Raiz

### Comportamento da API Pluggy para Cartões de Crédito

A API Pluggy **inverte a lógica** do campo `type` quando se trata de cartão de crédito:

| Transação | `type` da API | `amount` | Significado Real |
|-----------|--------------|----------|------------------|
| **Compra no cartão** | `"CREDIT"` | Positivo (+) | **DESPESA** para o usuário |
| **Pagamento da fatura** | `"CREDIT"` | Negativo (-) | Pagamento/redução de dívida |

### Por que isso acontece?

- Do ponto de vista **do banco emissor do cartão**, uma compra é um **crédito** (eles emprestam dinheiro para você)
- Do ponto de vista **do usuário**, uma compra é uma **despesa** (você gastou dinheiro)

A API Pluggy adota a perspectiva do banco, mas nosso sistema precisa adotar a perspectiva do usuário!

---

## ⚠️ Trecho dos Logs que Confirmam o Bug

```json
// Exemplo de COMPRA (gasto do usuário) retornada pela API:
{
  "description": "A FORMIGUINHA RIO DE JANEIR BRA",
  "amount": 12,
  "type": "CREDIT",  // ❌ API diz "CREDIT" mas é DESPESA!
  "category": "Groceries",
  "creditCardMetadata": {
    "cardNumber": "4274",
    "payeeMCC": 5921
  }
}
```

---

## ✅ Solução Implementada

### 1. **Ignorar o campo `type` para transações de cartão de crédito**

**Arquivo:** `gerente_financeiro/open_finance_oauth_handler.py`

**Mudança:**
```python
# ❌ ANTES (lógica ERRADA):
tipo = "Receita" if txn.type == "CREDIT" else "Despesa"

# ✅ DEPOIS (lógica CORRIGIDA):
if is_credit_card:
    # Para CC, IGNORAMOS o "type" da API
    # amount > 0 = GASTO (DESPESA)
    # amount < 0 = PAGAMENTO (ignorar)
    if float(txn.amount) < 0:
        # Pular pagamento de fatura
        continue
    else:
        tipo = "Despesa"  # SEMPRE despesa para compras
        logger.info(f"✅ CC: DESPESA (ignorando type='{txn.type}')")
else:
    # Conta corrente/poupança: lógica normal
    tipo = "Receita" if float(txn.amount) > 0 else "Despesa"
```

### 2. **Logs melhorados para debug**

Adicionamos o campo `type` da API aos logs:

```python
logger.info(f"🔍 Transação {txn.id}:")
logger.info(f"   💰 Amount: {float(txn.amount)}")
logger.info(f"   🏷️ Type API: {txn.type}")  # Agora logamos o type!
logger.info(f"   💳 Tipo conta: {account.type}")
logger.info(f"   ❓ É cartão crédito? {is_credit_card}")
```

### 3. **Comentários explicativos no código**

```python
# ⚠️ LÓGICA CORRIGIDA: Para cartão de crédito a API Pluggy INVERTE os types!
# - Compras (gastos): vêm como type="CREDIT" + amount positivo (mas é DESPESA)
# - Pagamentos fatura: vêm como type="CREDIT" + amount negativo (é pagamento)
#
# Nossa lógica: amount > 0 no CC = DESPESA, amount < 0 = pagamento (ignorar)
```

---

## 🎯 Impacto

### ✅ Transações Futuras
- Todas as **novas importações** após o deploy do fix estarão corretas
- Compras no cartão serão classificadas como **"Despesa"**

### ⚠️ Transações Já Importadas (ATENÇÃO!)
As transações que já foram importadas com classificação errada **NÃO serão corrigidas automaticamente**.

**Ações necessárias:**
1. **Usuário deve revisar manualmente** todas as transações de cartão importadas antes do fix
2. Usar o comando `/editar` para corrigir cada transação individualmente
3. Ou executar um script SQL de correção em massa (veja abaixo)

---

## 🔧 Script de Correção em Massa (Opcional)

Se houver muitas transações erradas, você pode executar este SQL diretamente no banco:

```sql
-- ATENÇÃO: Testar em ambiente de DEV primeiro!

-- Corrigir lançamentos de cartão de crédito que foram marcados como "Receita"
UPDATE lancamentos
SET tipo = 'Despesa'
WHERE forma_pagamento = 'Cartão de Crédito'
  AND tipo = 'Receita'
  AND valor > 0;

-- Ver quantos registros foram afetados:
SELECT COUNT(*) as corrigidos
FROM lancamentos
WHERE forma_pagamento = 'Cartão de Crédito'
  AND tipo = 'Despesa'
  AND created_at > '2025-11-01';  -- Ajustar data conforme necessário
```

**⚠️ IMPORTANTE:** Backup do banco antes de executar!

---

## 📊 Validação do Fix

### Como Testar:

1. **Sincronizar transações** com `/sincronizar`
2. **Importar uma compra de cartão** com `/importar_transacoes`
3. **Verificar logs** no Railway:
   ```
   ✅ Cartão de crédito: categorizando como DESPESA (amount positivo, ignorando type='CREDIT')
   ```
4. **Verificar no bot** que a transação aparece como "Despesa"

### Logs Esperados (Railway):

```
2025-11-18 14:46:53 - INFO - 🔍 Analisando transação xxx:
2025-11-18 14:46:53 - INFO -    📝 Descrição: A FORMIGUINHA
2025-11-18 14:46:53 - INFO -    💰 Amount: 12.0
2025-11-18 14:46:53 - INFO -    🏷️ Type API: CREDIT
2025-11-18 14:46:53 - INFO -    💳 Tipo conta: CREDIT
2025-11-18 14:46:53 - INFO -    ❓ É cartão crédito? True
2025-11-18 14:46:53 - INFO - ✅ Cartão de crédito: categorizando como DESPESA (ignorando type='CREDIT')
```

---

## 🔄 Commits Relacionados

| Commit | Descrição |
|--------|-----------|
| `9263c39` | **FIX principal** - Correção da lógica de classificação CC |
| `b931806` | Sistema de whitelist (não relacionado ao bug) |
| `67a45f4` | Documentação whitelist (não relacionado ao bug) |

---

## 📚 Referências

- **Issue Original:** Usuário reportou via screenshot do Telegram (18/11/2025 11:47)
- **Logs Railway:** `2025-11-18T14:46:42` até `2025-11-18T14:47:59`
- **API Pluggy:** https://docs.pluggy.ai/#tag/Transactions
- **Arquivo Modificado:** `gerente_financeiro/open_finance_oauth_handler.py` (linhas 1778-1816, 1898-1920)

---

## 💡 Lições Aprendidas

1. **Sempre logar os campos críticos da API** (como `type`) para debug
2. **Documentar inversões de lógica** de APIs externas no código
3. **Adicionar testes automáticos** para classificação de transações
4. **Não confiar cegamente** no campo `type` sem entender seu contexto
5. **Sempre considerar a perspectiva do usuário** vs perspectiva do sistema bancário

---

## ✅ Status

- ✅ **Fix implementado** (commit 9263c39)
- ✅ **Deploy realizado** (Railway)
- ✅ **Logs validados** (type da API aparece nos logs)
- ⏳ **Aguardando validação do usuário** (teste real com próxima sincronização)
- ⏳ **Transações antigas** (pendente correção manual ou script SQL)

---

**Última atualização:** 18/11/2025 11:50 BRT
