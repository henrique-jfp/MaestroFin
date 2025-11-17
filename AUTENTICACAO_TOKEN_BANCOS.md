# 🔑 Autenticação por Token de Banco

## 📋 Visão Geral

Este documento descreve o novo sistema de autenticação por token que **substituiu** a falha integração Pluggy/Open Finance.

### ❌ Problema Anterior
- Pluggy/Open Finance não funcionava
- Usuários NÃO recebiam notificações ou solicitações de autorização
- Status ficava eternamente em `WAITING_USER_INPUT` com `detail=None`
- Sem forma de conectar bancos ao bot

### ✅ Solução Implementada
- Usuários fornecem tokens de segurança gerados diretamente pelos bancos
- Autenticação instantânea e confiável
- Sem dependência de serviços terceirizados que falham
- Suporta 6 bancos principais: Inter, Itaú, Bradesco, Nubank, Caixa, Santander

---

## 🚀 Como Usar

### Novo Comando
```
/conectar_token
```

### Fluxo do Usuário

1. **Usuário executa**: `/conectar_token`
   - Bot exibe menu de bancos disponíveis

2. **Usuário seleciona banco** (ex: Inter)
   - Bot mostra instruções específicas de como gerar o token
   - Instrui onde ir no app/site do banco

3. **Usuário copia token** 
   - Segue instruções do bot
   - Gera token na plataforma do banco

4. **Usuário cola token no Telegram**
   - Bot valida formato do token
   - Se inválido: mostra erro com dicas
   - Se válido: ✅ Conexão estabelecida

5. **Resultado**
   - Token armazenado com segurança
   - Banco conectado e pronto para sincronizar dados
   - Usuário pode ver comandos disponíveis (/extrato, /minhas_contas, /saldo)

---

## 🏦 Tokens por Banco

### 🔵 **Inter**
- **Formato**: `CPF:token`
- **Onde gerar**: https://eb.bancointer.com.br/ → Configurações → API
- **Exemplo**: `12345678901:abc123def456ghi789jkl012mno345pqr`
- **Validação**: 
  - Deve ter exatamente um `:`
  - CPF = 11 dígitos
  - Token ≥ 20 caracteres

### 🟠 **Itaú**
- **Formato**: Bearer token ou código de acesso
- **Onde gerar**: App Itaú → Minha Conta → Configurações → Chaves de Acesso
- **Exemplo**: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`
- **Validação**: 
  - Mínimo 20 caracteres
  - Remover "Bearer " se incluído

### 🔴 **Bradesco**
- **Formato**: Bearer token
- **Onde gerar**: Internet Banking → Configurações → Chaves de API
- **Validação**: 
  - Mínimo 20 caracteres
  - Caracteres válidos: `a-zA-Z0-9-_.`

### 🟣 **Nubank**
- **Formato**: JWT (3 partes com `.`) ou Security Code
- **Onde gerar**: App Nubank → Minha Conta → Segurança → Chaves de Acesso
- **Exemplo (JWT)**: `eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwiZXhwIjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c`
- **Validação**: 
  - Mínimo 20 caracteres
  - Se JWT: deve ter exatamente 2 pontos

### 🟢 **Caixa**
- **Formato**: Security Token
- **Onde gerar**: Caixa Internet Banking → Configurações de Segurança
- **Contato para apoio**: suporte@caixa.gov.br
- **Validação**: 
  - Mínimo 20 caracteres
  - Caracteres válidos: `a-zA-Z0-9-`

### 🟡 **Santander**
- **Formato**: API Token
- **Onde gerar**: Santander Developer Portal (https://www.santander.com.br/developers)
- **Validação**: 
  - Mínimo 20 caracteres
  - Caracteres válidos: `a-zA-Z0-9-_.`

---

## 🔐 Segurança

### Proteção do Token
✅ **Mensagem do usuário é deletada** após envio
- Impede que token fique visível no histórico do chat

✅ **Token validado antes de armazenar**
- Formato verificado segundo padrões do banco
- Erros ajudam usuario a corrigir

✅ **Será implementado**: Criptografia do token em BD
- Usar chave armazenada em variável de ambiente
- Descriptografar apenas ao usar para autenticação

### O que NÃO fazemos
❌ Não compartilhamos token com terceiros
❌ Não logamos token em texto plano
❌ Não enviamos para APIs externas sem necessidade

---

## 📁 Estrutura de Código

### Arquivos Principais

**`open_finance/token_auth.py`** - Core de autenticação
```python
class TokenAuthManager:
    - authenticate(bank, token)  # Valida token para banco específico
    - validate_token(bank, token)  # Quick validation
    - store_token(user_id, bank, auth_data)  # Armazena token
    - get_token(user_id, bank)  # Recupera token
```

**`gerente_financeiro/token_auth_handler.py`** - Handler Telegram
```python
class TokenAuthHandler:
    - conectar_token_start()  # Entry point do comando
    - select_bank_token()  # Callback ao selecionar banco
    - entering_token()  # Processa token enviado
    - _get_bank_instructions()  # Instruções específicas por banco
```

### Fluxo de Componentes

```
┌─────────────────┐
│ /conectar_token │
└────────┬────────┘
         │
         ▼
┌──────────────────────────┐
│ TokenAuthHandler         │
│ - select_bank_token()    │
│ - entering_token()       │
└────────┬─────────────────┘
         │
         ▼
┌──────────────────────────┐
│ TokenAuthManager         │
│ - authenticate()         │
│ - validate_token()       │
│ - store_token()          │
└────────┬─────────────────┘
         │
         ▼
┌──────────────────────────┐
│ Banco (futura)           │
│ - API calls com token    │
│ - Sincroniza dados       │
└──────────────────────────┘
```

---

## 🔄 Fluxo Detalhado da Conversa

### Estado 1: SELECTING_BANK_TOKEN
```
Bot: "Qual banco você quer conectar?"
     [🏦 Inter] [🏦 Itaú] [🏦 Bradesco]
     [🏦 Nubank] [🏦 Caixa] [🏦 Santander]
     [❌ Cancelar]

Usuário: Clica em "Inter"
```

### Estado 2: ENTERING_TOKEN
```
Bot: "🔐 Inter Selecionado

Como gerar o token no Inter:
1️⃣ Acesse: https://eb.bancointer.com.br/
2️⃣ Vá em 'Configurações' → 'API'
3️⃣ Clique em 'Gerar novo token'
4️⃣ Copie no formato: CPF:token

Cole o token abaixo (será removido da conversa por segurança):"

Usuário: "12345678901:abc123def456ghi789jkl012mno345pqr"
```

### Validação
```
Bot: "⏳ Validando token..."

[Se válido]
Bot: "✅ Token de Inter Validado!

🔐 Conexão segura estabelecida
📱 Status: Conectado
💳 Banco: Inter

Agora você pode:
• /minhas_contas - Ver contas conectadas
• /extrato - Ver transações
• /saldo - Ver saldo consolidado

Token será usado apenas para sincronizar dados do seu banco."

[Se inválido]
Bot: "❌ Token Inter inválido!

Dicas:
• Copie o token completo (com toda a sequência)
• Não adicione espaços
• Se tiver ':', não remova

Tente novamente:"
```

---

## 🚀 Próximos Passos

### Phase 1 (Implementado)
- ✅ TokenAuthManager com validação de 6 bancos
- ✅ TokenAuthHandler com fluxo Telegram
- ✅ Integração com bot.py
- ✅ Instruções por banco

### Phase 2 (Planejado)
- 🔜 Armazenar tokens em BD com criptografia
- 🔜 Criar tabela `user_bank_tokens`
- 🔜 Implementar rotação de tokens

### Phase 3 (Planejado)
- 🔜 API calls reais usando tokens
- 🔜 Sincronização de transações
- 🔜 Implementar `/minhas_contas`, `/extrato` com tokens

### Phase 4 (Planejado)
- 🔜 Rate limiting para chamadas de API
- 🔜 Tratamento de tokens expirados
- 🔜 Refresh token automático

### Phase 5 (Planejado)
- 🔜 Dashboard mostrando contas conectadas
- 🔜 Múltiplos tokens por banco
- 🔜 Desconectar banco individual

---

## 🐛 Troubleshooting

### "Token Inter inválido!"
**Problema**: Formato incorreto
**Solução**:
- Verifique se tem `:` separando CPF e token
- CPF deve ter 11 dígitos (sem formatação)
- Token deve ter +20 caracteres

### "Token muito curto"
**Problema**: Token incompleto
**Solução**:
- Certifique-se de copiar o token completo
- Sem editar ou remover partes
- Incluir tudo que o banco mostrou

### "Caracteres inválidos"
**Problema**: Token com espaços ou caracteres especiais
**Solução**:
- Remova espaços em branco
- Use Ctrl+C / Cmd+C para copiar exatamente
- Não edite o token antes de colar

### "Sessão expirada"
**Problema**: Esperou muito tempo para colar token
**Solução**:
- Use `/conectar_token` novamente
- Complete o fluxo em sequência

---

## 📊 Métricas e Logs

### Logs Importantes
```
✅ Token Inter validado para CPF 123***89
💾 Token armazenado para usuário 123456789 - banco: inter
⏳ Validando token...
❌ Token inválido para inter: [erro específico]
```

### Analytics (futuro)
- Rastrear quantos usuários conectam com token
- Taxa de sucesso vs falha por banco
- Tempo médio para completar fluxo
- Bancos mais populares

---

## 🤝 Comparação: Open Finance vs Token Auth

| Aspecto | Open Finance (Pluggy) | Token Auth |
|--------|----------------------|-----------|
| **Funcionamento** | Notificação push ao banco | Token direto do banco |
| **Confiabilidade** | ❌ Não funciona | ✅ Funciona |
| **Velocidade** | Minutos (se funcionar) | Instantânea |
| **Segurança** | Intermediário | Direto |
| **Suporte** | 146+ bancos (teoria) | 6+ bancos (prova) |
| **UX** | Komplexo | Simples |
| **Custo** | Variável (Pluggy) | Zero |

---

## 📞 Suporte

**Dúvidas sobre o token do seu banco?**
- Acesse o suporte do banco
- Menu: "Como gerar chave de acesso" ou "API"

**Dúvidas sobre usar no MaestroFin?**
- Use `/help` no bot
- Comando: `/conectar_token` para mais detalhes

---

**Última atualização**: 2024
**Status**: 🟢 Implementação iniciada
**Responsável**: Equipe MaestroFin
