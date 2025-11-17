# 🏦 Guia de Conexão com Bancos - Maestro Financeiro

## 📱 Como Conectar Seu Banco

### Passo a Passo:

1. **Inicie a conexão**
   - Digite `/conectar_banco` no chat do Telegram
   - Escolha seu banco na lista de opções

2. **Informe as credenciais**
   - Informe seu usuário/CPF/email (como você faz login no app)
   - Informe sua senha
   - Outras informações que forem solicitadas

3. **Autorize no app do banco**
   - Você verá a mensagem: "⚠️ Autorização Bancária Necessária"
   - O bot explicará o que fazer
   - Abra o app do seu banco ou internet banking
   - Procure por notificações de segurança/confirmação
   - Autorize o acesso (pode ser via OTP, token, fingerprint ou código)

4. **Voltando ao bot**
   - Após autorizar no app, volte ao Telegram
   - Clique no botão "✅ Já autorizei! Tentar novamente"
   - O bot verificará a autorização (demora poucos segundos)

5. **Pronto! 🎉**
   - Se tudo correr bem, suas contas estarão conectadas
   - Você verá o saldo das contas
   - Use `/minhas_contas` e `/extrato` para consultar dados

---

## ⚠️ Problemas Comuns

### "Erro ao carregar lista de bancos"
**Causa**: Problema de conexão com o Pluggy (plataforma Open Finance)
**Solução**:
- Aguarde alguns minutos
- Tente novamente com `/conectar_banco`
- Verifique sua conexão de internet

### "O banco rejeitou as credenciais"
**Causa**: Usuário/senha incorretos
**Solução**:
- Verifique se o usuário/CPF/email está correto
- Verifique a senha (certifique-se de CAPS LOCK)
- Tente conectar direto no app/internet banking para confirmar
- Tente novamente com `/conectar_banco`

### "Esperando confirmação adicional" (WAITING_USER_INPUT)
**Causa**: O banco pediu autorização extra de segurança
**Solução**:
- Abra o app do seu banco IMEDIATAMENTE
- Procure por:
  - Notificação push de segurança
  - SMS com código
  - Email com link de confirmação
  - Pop-up na tela pedindo confirmação
- Autorize o acesso
- Volte ao Telegram e clique "Já autorizei! Tentar novamente"
- Pode levar de 30 segundos a 5 minutos

### Nenhuma conta aparece após conectar
**Causa**: Contas estão sendo carregadas ou sem permissão
**Solução**:
- Aguarde alguns minutos
- Use `/minhas_contas` para verificar
- Confirme que suas contas têm permissão no app do banco
- Tente desconectar e reconectar

### "Muitas tentativas de reconexão"
**Causa**: Você tentou mais de 3 vezes e ainda não autorizou
**Solução**:
- Desista desta tentativa
- Aguarde 5 minutos
- Use `/conectar_banco` para começar do zero
- Certifique-se de autorizar no app dentro de 5 minutos

---

## 🔒 Segurança

### Como seus dados são protegidos?

1. **Criptografia End-to-End**: Todos os dados são transmitidos através de conexões HTTPS criptografadas
2. **Sem Armazenamento de Senhas**: Nunca armazenamos suas senhas - elas são usadas apenas para autenticação
3. **Open Finance**: Usamos o protocolo Open Finance do Banco Central do Brasil
4. **Acesso Controlado**: Você autoriza explicitamente cada conexão no app do seu banco
5. **Remoção Automática**: Suas informações sensíveis são removidas da conversa automaticamente

### Qual informação o bot vê?

- ✅ Saldo das contas
- ✅ Tipo de conta (corrente, poupança, etc)
- ✅ Transações (últimos 30 dias)
- ❌ Senha (nunca armazenada ou vista após autenticação)
- ❌ Dados pessoais além do necessário

---

## 📋 Bancos Suportados

Atualmente suportamos:
- ✅ Inter
- ✅ Itaú
- ✅ Bradesco
- ✅ Nubank
- ✅ Caixa
- ✅ Santander
- (+ 146 conectores pelo Pluggy)

---

## 🆘 Precisa de Ajuda?

Se continuar tendo problemas:
1. Verifique este guia novamente
2. Tente com outro banco para descartar problemas gerais
3. Aguarde 1 hora e tente novamente (pode ser problema temporário do banco)
4. Entre em contato com o suporte

---

## 💡 Dicas Importantes

### ⏰ Timing
- Autorização geralmente é instantânea
- Pode levar até 5 minutos em casos raros
- Se passar de 10 minutos, cancelar e tentar novamente

### 🏦 No app do banco
- Fique de olho em notificações
- Alguns bancos enviam por SMS ou email
- Confirme IMEDIATAMENTE após receber
- Não feche o app durante o processo

### 🔄 Reconexões
- Pode desconectar e reconectar a qualquer hora
- Use `/desconectar_banco` para remover uma conexão
- Seus dados locais NÃO são removidos, apenas a sincronização

---

## 📊 Após Conectar

Com seu banco conectado, você pode:

- **/minhas_contas** - Ver todas as contas conectadas e saldos
- **/extrato** - Ver últimas transações
- **/saldo** - Ver saldo consolidado
- Usar dados para criar gráficos e análises

---

**Versão**: 1.0  
**Última atualização**: Nov 2025
