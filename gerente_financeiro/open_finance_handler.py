"""
🏦 Handler Open Finance - Comandos Telegram
Gerencia interação do usuário com conexões bancárias
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters
)
from datetime import datetime
from open_finance.bank_connector import BankConnector
from open_finance.pluggy_client import PluggyClient, format_currency, format_account_type

logger = logging.getLogger(__name__)

# Estados da conversa
SELECTING_BANK, ENTERING_CREDENTIALS = range(2)


class OpenFinanceHandler:
    """Handler para comandos Open Finance"""
    
    def __init__(self):
        self.connector = BankConnector()
        self.client = PluggyClient()
    
    # ==================== /conectar_banco ====================
    
    async def conectar_banco_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Inicia processo de conexão com banco"""
        user_id = update.effective_user.id
        
        logger.info(f"👤 Usuário {user_id} iniciando conexão bancária")
        
        try:
            # Listar bancos disponíveis
            connectors = self.client.list_connectors(country="BR")
            
            # Filtrar principais bancos (top 20)
            main_banks = [c for c in connectors if c.get('featured', False)][:20]
            
            if not main_banks:
                main_banks = connectors[:20]
            
            # Criar teclado inline
            keyboard = []
            for bank in main_banks:
                keyboard.append([
                    InlineKeyboardButton(
                        bank['name'],
                        callback_data=f"bank_{bank['id']}"
                    )
                ])
            
            keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="cancel")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            message = (
                "🏦 <b>Conectar Banco</b>\n\n"
                "Selecione sua instituição financeira:\n\n"
                "<i>Seus dados são criptografados e seguros. "
                "Usamos Open Finance do Banco Central.</i>"
            )
            
            await update.message.reply_text(
                message,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
            
            # Salvar lista de conectores no contexto
            context.user_data['connectors'] = {str(c['id']): c for c in connectors}
            
            return SELECTING_BANK
            
        except Exception as e:
            logger.error(f"❌ Erro ao listar bancos: {e}")
            await update.message.reply_text(
                "❌ Erro ao carregar lista de bancos. Tente novamente mais tarde."
            )
            return ConversationHandler.END
    
    async def conectar_banco_selected(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Banco selecionado - solicitar credenciais"""
        query = update.callback_query
        await query.answer()
        
        if query.data == "cancel":
            await query.edit_message_text("❌ Conexão cancelada.")
            return ConversationHandler.END
        
        connector_id = query.data.replace("bank_", "")
        connector = context.user_data['connectors'].get(connector_id)
        
        if not connector:
            await query.edit_message_text("❌ Banco não encontrado.")
            return ConversationHandler.END
        
        # Salvar conector selecionado
        context.user_data['selected_connector'] = connector
        
        # Obter campos de credenciais necessários
        credentials = connector.get('credentials', [])
        
        message = (
            f"🔐 <b>{connector['name']}</b>\n\n"
            f"Digite suas credenciais no formato:\n\n"
        )
        
        # Exemplo de formato baseado nos campos
        examples = []
        for cred in credentials:
            field_name = cred.get('label', cred.get('name', 'Campo'))
            examples.append(f"<code>{field_name}: valor</code>")
        
        message += "\n".join(examples)
        message += (
            "\n\n<b>Exemplo:</b>\n"
            "<code>CPF: 12345678900\n"
            "Senha: minhasenha123</code>\n\n"
            "<i>⚠️ Suas credenciais NÃO são armazenadas!</i>"
        )
        
        await query.edit_message_text(message, parse_mode='HTML')
        
        return ENTERING_CREDENTIALS
    
    async def conectar_banco_credentials(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Recebe credenciais e cria conexão"""
        user_id = update.effective_user.id
        connector = context.user_data.get('selected_connector')
        
        if not connector:
            await update.message.reply_text("❌ Sessão expirada. Use /conectar_banco novamente.")
            return ConversationHandler.END
        
        # Parsear credenciais do texto
        text = update.message.text.strip()
        credentials = {}
        
        try:
            for line in text.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    credentials[key.strip().lower()] = value.strip()
            
            if not credentials:
                await update.message.reply_text(
                    "❌ Formato inválido. Use o formato:\n"
                    "<code>Campo: Valor</code>",
                    parse_mode='HTML'
                )
                return ENTERING_CREDENTIALS
            
            # Deletar mensagem com credenciais (segurança)
            try:
                await update.message.delete()
            except:
                pass
            
            # Enviar mensagem de processamento
            processing_msg = await update.message.reply_text(
                "⏳ Conectando com o banco...\n"
                "Isso pode levar alguns segundos."
            )
            
            # Criar conexão
            connection = self.connector.create_connection(
                user_id=user_id,
                connector_id=int(connector['id']),
                credentials=credentials
            )
            
            # Sincronizar transações
            self.connector.sync_transactions(connection['id'], days=30)
            
            # Sucesso!
            await processing_msg.edit_text(
                f"✅ <b>Banco conectado com sucesso!</b>\n\n"
                f"🏦 {connector['name']}\n"
                f"📅 {connection['created_at'].strftime('%d/%m/%Y %H:%M')}\n\n"
                f"Use /minhas_contas para ver suas contas\n"
                f"Use /saldo para ver saldo consolidado\n"
                f"Use /extrato para ver transações recentes",
                parse_mode='HTML'
            )
            
            # Limpar contexto
            context.user_data.clear()
            
            return ConversationHandler.END
            
        except Exception as e:
            logger.error(f"❌ Erro ao conectar banco: {e}")
            await update.message.reply_text(
                f"❌ Erro ao conectar: {str(e)}\n\n"
                f"Verifique suas credenciais e tente novamente."
            )
            return ConversationHandler.END
    
    # ==================== /minhas_contas ====================
    
    async def minhas_contas(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Lista contas bancárias conectadas"""
        user_id = update.effective_user.id
        
        try:
            accounts = self.connector.list_accounts(user_id)
            
            if not accounts:
                await update.message.reply_text(
                    "📭 Você ainda não tem contas conectadas.\n\n"
                    "Use /conectar_banco para conectar sua primeira conta!"
                )
                return
            
            message = "💳 <b>Suas Contas</b>\n\n"
            
            total = 0.0
            for account in accounts:
                account_type_emoji = format_account_type(account['account_type'])
                balance = account['balance']
                total += balance
                
                message += (
                    f"{account_type_emoji}\n"
                    f"<b>{account['bank_name']}</b>\n"
                    f"{account['account_name'] or 'Conta'}\n"
                    f"Saldo: <b>{format_currency(balance)}</b>\n\n"
                )
            
            message += (
                f"━━━━━━━━━━━━━━━━\n"
                f"💰 <b>Total: {format_currency(total)}</b>"
            )
            
            await update.message.reply_text(message, parse_mode='HTML')
            
        except Exception as e:
            logger.error(f"❌ Erro ao listar contas: {e}")
            await update.message.reply_text(
                "❌ Erro ao buscar contas. Tente novamente."
            )
    
    # ==================== /saldo ====================
    
    async def saldo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mostra saldo consolidado"""
        user_id = update.effective_user.id
        
        try:
            total = self.connector.get_total_balance(user_id)
            accounts = self.connector.list_accounts(user_id)
            
            if not accounts:
                await update.message.reply_text(
                    "📭 Você ainda não tem contas conectadas.\n\n"
                    "Use /conectar_banco para começar!"
                )
                return
            
            message = (
                "💰 <b>Saldo Consolidado</b>\n\n"
                f"<b>{format_currency(total)}</b>\n\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"📊 {len(accounts)} conta(s) conectada(s)\n"
                f"🕐 Atualizado agora\n\n"
                f"<i>Dados em tempo real via Open Finance</i>"
            )
            
            await update.message.reply_text(message, parse_mode='HTML')
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar saldo: {e}")
            await update.message.reply_text(
                "❌ Erro ao calcular saldo. Tente novamente."
            )
    
    # ==================== /extrato ====================
    
    async def extrato(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mostra transações recentes"""
        user_id = update.effective_user.id
        
        try:
            transactions = self.connector.list_transactions(user_id, limit=20, days=30)
            
            if not transactions:
                await update.message.reply_text(
                    "📭 Nenhuma transação encontrada nos últimos 30 dias.\n\n"
                    "Use /conectar_banco se ainda não conectou seu banco."
                )
                return
            
            message = "📊 <b>Extrato - Últimos 30 dias</b>\n\n"
            
            for trans in transactions:
                date = trans['date'].strftime('%d/%m')
                amount = trans['amount']
                emoji = "💰" if amount > 0 else "💸"
                
                message += (
                    f"{emoji} <b>{format_currency(abs(amount))}</b>\n"
                    f"{trans['description']}\n"
                    f"📅 {date} • {trans['bank']}\n\n"
                )
                
                # Limitar tamanho da mensagem
                if len(message) > 3500:
                    message += f"<i>... e mais {len(transactions) - transactions.index(trans) - 1} transações</i>"
                    break
            
            message += "\n<i>💡 Dados sincronizados via Open Finance</i>"
            
            await update.message.reply_text(message, parse_mode='HTML')
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar extrato: {e}")
            await update.message.reply_text(
                "❌ Erro ao buscar transações. Tente novamente."
            )
    
    # ==================== /desconectar_banco ====================
    
    async def desconectar_banco(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Remove conexão bancária"""
        user_id = update.effective_user.id
        
        try:
            connections = self.connector.list_connections(user_id)
            
            if not connections:
                await update.message.reply_text(
                    "📭 Você não tem bancos conectados."
                )
                return
            
            # Criar teclado com bancos
            keyboard = []
            for conn in connections:
                keyboard.append([
                    InlineKeyboardButton(
                        f"🗑️ {conn['connector_name']}",
                        callback_data=f"disconnect_{conn['id']}"
                    )
                ])
            
            keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="cancel")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "🗑️ <b>Desconectar Banco</b>\n\n"
                "Selecione o banco que deseja remover:",
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
            
        except Exception as e:
            logger.error(f"❌ Erro ao desconectar: {e}")
            await update.message.reply_text(
                "❌ Erro ao processar desconexão. Tente novamente."
            )
    
    async def desconectar_banco_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Confirma e remove conexão"""
        query = update.callback_query
        await query.answer()
        
        if query.data == "cancel":
            await query.edit_message_text("❌ Cancelado.")
            return
        
        connection_id = int(query.data.replace("disconnect_", ""))
        
        try:
            success = self.connector.delete_connection(connection_id)
            
            if success:
                await query.edit_message_text(
                    "✅ Banco desconectado com sucesso!\n\n"
                    "Todas as contas e transações foram removidas."
                )
            else:
                await query.edit_message_text(
                    "❌ Erro ao desconectar banco."
                )
                
        except Exception as e:
            logger.error(f"❌ Erro ao confirmar desconexão: {e}")
            await query.edit_message_text(
                "❌ Erro ao desconectar banco."
            )
    
    # ==================== Handlers ====================
    
    def get_handlers(self):
        """Retorna handlers para registrar no bot"""
        
        # ConversationHandler para /conectar_banco
        connect_handler = ConversationHandler(
            entry_points=[CommandHandler('conectar_banco', self.conectar_banco_start)],
            states={
                SELECTING_BANK: [
                    CallbackQueryHandler(self.conectar_banco_selected)
                ],
                ENTERING_CREDENTIALS: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.conectar_banco_credentials)
                ]
            },
            fallbacks=[CommandHandler('cancelar', lambda u, c: ConversationHandler.END)]
        )
        
        return [
            connect_handler,
            CommandHandler('minhas_contas', self.minhas_contas),
            CommandHandler('saldo', self.saldo),
            CommandHandler('extrato', self.extrato),
            CommandHandler('desconectar_banco', self.desconectar_banco),
            CallbackQueryHandler(self.desconectar_banco_confirm, pattern='^disconnect_')
        ]
