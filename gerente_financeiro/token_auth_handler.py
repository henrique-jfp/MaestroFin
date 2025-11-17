"""
🔑 Handler de Autenticação por Token
Permite que usuários conectem bancos usando tokens de segurança
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters, ConversationHandler
from open_finance.token_auth import token_manager

logger = logging.getLogger(__name__)

# Estados
SELECTING_BANK_TOKEN, ENTERING_TOKEN = range(2)


class TokenAuthHandler:
    """Handler para autenticação por token"""
    
    def __init__(self):
        self.supported_banks = {
            'inter': 'Inter',
            'itau': 'Itaú',
            'bradesco': 'Bradesco',
            'nubank': 'Nubank',
            'caixa': 'Caixa',
            'santander': 'Santander',
        }
    
    async def conectar_token_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Inicia processo de conexão com token"""
        user_id = update.effective_user.id
        
        logger.info(f"👤 Usuário {user_id} iniciando autenticação por token")
        
        # Criar teclado com bancos disponíveis
        keyboard = []
        for bank_key, bank_name in self.supported_banks.items():
            keyboard.append([
                InlineKeyboardButton(
                    f"🏦 {bank_name}",
                    callback_data=f"token_bank_{bank_key}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="token_cancel")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = (
            "🔑 <b>Conectar com Token de Segurança</b>\n\n"
            "Este método é mais simples que Open Finance!\n\n"
            "<b>Como funciona:</b>\n"
            "1️⃣ Você gera um token no app/site do seu banco\n"
            "2️⃣ Cola o token aqui\n"
            "3️⃣ Pronto! Conectado instantaneamente\n\n"
            "<b>Qual banco você quer conectar?</b>"
        )
        
        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='HTML')
        
        context.user_data['selected_bank_token'] = None
        return SELECTING_BANK_TOKEN
    
    async def select_bank_token(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Banco selecionado - solicitar token"""
        query = update.callback_query
        await query.answer()
        
        if query.data == "token_cancel":
            await query.edit_message_text("❌ Autenticação cancelada.")
            return ConversationHandler.END
        
        bank_key = query.data.replace("token_bank_", "")
        
        if bank_key not in self.supported_banks:
            await query.edit_message_text("❌ Banco não suportado.")
            return ConversationHandler.END
        
        bank_name = self.supported_banks[bank_key]
        context.user_data['selected_bank_token'] = bank_key
        
        # Instruções específicas por banco
        instructions = self._get_bank_instructions(bank_key)
        
        message = (
            f"🔐 <b>{bank_name} Selecionado</b>\n\n"
            f"{instructions}\n\n"
            "Cole o token abaixo (será removido da conversa por segurança):"
        )
        
        await query.edit_message_text(message, parse_mode='HTML')
        
        return ENTERING_TOKEN
    
    async def entering_token(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Recebe e valida o token"""
        user_id = update.effective_user.id
        bank_key = context.user_data.get('selected_bank_token')
        token = update.message.text.strip()
        
        if not bank_key:
            await update.message.reply_text("❌ Sessão expirada. Use /conectar_token novamente.")
            context.user_data.clear()
            return ConversationHandler.END
        
        bank_name = self.supported_banks.get(bank_key, 'Banco')
        
        # Remover a mensagem do usuário por segurança
        try:
            await update.message.delete()
        except Exception:
            pass
        
        # Validar token
        processing_msg = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="⏳ Validando token..."
        )
        
        try:
            # Validar formato do token
            auth_data = token_manager.authenticate(bank_key, token)
            
            # Armazenar token
            token_manager.store_token(user_id, bank_key, auth_data)
            
            message = (
                f"✅ <b>Token de {bank_name} Validado!</b>\n\n"
                f"🔐 Conexão segura estabelecida\n"
                f"📱 Status: Conectado\n"
                f"💳 Banco: {bank_name}\n\n"
                f"Agora você pode:\n"
                f"• /minhas_contas - Ver contas conectadas\n"
                f"• /extrato - Ver transações\n"
                f"• /saldo - Ver saldo consolidado\n\n"
                f"<i>Token será usado apenas para sincronizar dados do seu banco.</i>"
            )
            
            await processing_msg.edit_text(message, parse_mode='HTML')
            
            context.user_data.clear()
            return ConversationHandler.END
            
        except ValueError as e:
            error_msg = f"❌ {str(e)}\n\n" \
                       f"<b>Dicas:</b>\n" \
                       f"• Copie o token completo (com toda a sequência)\n" \
                       f"• Não adicione espaços\n" \
                       f"• Se tiver ':', não remova\n\n" \
                       f"Tente novamente:"
            
            await processing_msg.edit_text(error_msg, parse_mode='HTML')
            return ENTERING_TOKEN
        
        except Exception as e:
            logger.error(f"Erro ao validar token: {e}")
            error_msg = (
                f"❌ Erro ao validar token\n\n"
                f"{str(e)}\n\n"
                f"Tente novamente ou use /cancelar"
            )
            
            await processing_msg.edit_text(error_msg)
            return ENTERING_TOKEN
    
    def _get_bank_instructions(self, bank_key: str) -> str:
        """Retorna instruções específicas para cada banco"""
        
        instructions = {
            'inter': (
                "<b>Como gerar o token no Inter:</b>\n"
                "1️⃣ Acesse: https://eb.bancointer.com.br/\n"
                "2️⃣ Vá em 'Configurações' → 'API'\n"
                "3️⃣ Clique em 'Gerar novo token'\n"
                "4️⃣ Copie no formato: CPF:token\n"
                "\n<i>Exemplo: 12345678901:abc123def456...</i>"
            ),
            'itau': (
                "<b>Como gerar o token no Itaú:</b>\n"
                "1️⃣ Abra o App do Itaú\n"
                "2️⃣ Vá em 'Minha Conta' → 'Configurações'\n"
                "3️⃣ Procure por 'Chaves de Acesso' ou 'Tokens'\n"
                "4️⃣ Gere um novo token\n"
                "5️⃣ Copie e cole aqui"
            ),
            'bradesco': (
                "<b>Como gerar o token no Bradesco:</b>\n"
                "1️⃣ Acesse o Internet Banking\n"
                "2️⃣ Vá em 'Configurações' ou 'Segurança'\n"
                "3️⃣ Procure por 'Chaves de API' ou 'Tokens'\n"
                "4️⃣ Gere um novo token\n"
                "5️⃣ Copie e cole aqui"
            ),
            'nubank': (
                "<b>Como gerar o token no Nubank:</b>\n"
                "1️⃣ Abra o App Nubank\n"
                "2️⃣ Toque em 'Minha Conta'\n"
                "3️⃣ Vá em 'Segurança' → 'Chaves de Acesso'\n"
                "4️⃣ Gere um novo token\n"
                "5️⃣ Copie e cole aqui"
            ),
            'caixa': (
                "<b>Como gerar o token na Caixa:</b>\n"
                "1️⃣ Acesse: https://www.caixa.gov.br/\n"
                "2️⃣ Entre no Internet Banking\n"
                "3️⃣ Procure por 'Chaves de Segurança'\n"
                "4️⃣ Gere um novo token\n"
                "5️⃣ Copie e cole aqui"
            ),
            'santander': (
                "<b>Como gerar o token no Santander:</b>\n"
                "1️⃣ Acesse: https://www.santander.com.br/\n"
                "2️⃣ Desenvolvedores → Sandbox\n"
                "3️⃣ Gere um novo token de acesso\n"
                "4️⃣ Copie e cole aqui"
            ),
        }
        
        return instructions.get(bank_key, "Cole o token gerado no seu banco:")
    
    async def cancel_conversation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancela a autenticação"""
        if update.message:
            await update.message.reply_text("❌ Autenticação cancelada.")
        context.user_data.clear()
        return ConversationHandler.END
    
    def get_conversation_handler(self):
        """Retorna ConversationHandler para registrar no bot"""
        from telegram.ext import CallbackQueryHandler
        
        token_conv = ConversationHandler(
            entry_points=[CommandHandler('conectar_token', self.conectar_token_start)],
            states={
                SELECTING_BANK_TOKEN: [
                    CallbackQueryHandler(self.select_bank_token)
                ],
                ENTERING_TOKEN: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.entering_token)
                ]
            },
            fallbacks=[CommandHandler('cancelar', self.cancel_conversation)]
        )
        
        return token_conv
