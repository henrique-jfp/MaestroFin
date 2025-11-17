"""
🏦 Handler Open Finance - Comandos Telegram
Gerencia interação do usuário com conexões bancárias
"""

import asyncio
import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ForceReply, ReplyKeyboardRemove
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters
)
from datetime import datetime
from open_finance.bank_connector import (
    BankConnector,
    BankConnectorError,
    BankConnectorAdditionalAuthRequired,
    BankConnectorTimeout,
    BankConnectorUserActionRequired,
)
from open_finance.pluggy_client import PluggyClient, format_currency, format_account_type

logger = logging.getLogger(__name__)

# Estados da conversa
SELECTING_BANK, ENTERING_FIELD = range(2)


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

            # Limitar para bancos suportados (PF)
            allowed_banks = [
                {
                    "label": "Inter",
                    "keywords": ["inter"],
                },
                {
                    "label": "Itaú",
                    "keywords": ["itaú", "itau"],
                },
                {
                    "label": "Bradesco",
                    "keywords": ["bradesco"],
                },
                {
                    "label": "Nubank",
                    "keywords": ["nubank", "nu bank"],
                },
                {
                    "label": "Caixa",
                    "keywords": ["caixa", "cef"],
                },
                {
                    "label": "Santander",
                    "keywords": ["santander"],
                },
            ]

            blocked_terms = [
                "empresa",
                "empresas",
                "empresarial",
                "business",
                "corporate",
                "pj",
                "bba",
                "pro",
                "emps",
            ]

            def is_blocked(name_lower: str) -> bool:
                return any(term in name_lower for term in blocked_terms)

            # Seleciona conectores na ordem desejada, sem duplicar nomes
            selected_connectors = []
            used_connector_ids = set()

            for bank_cfg in allowed_banks:
                matches = []
                for conn in connectors:
                    connector_name = (conn.get('name') or '').strip()
                    if not connector_name:
                        continue
                    if conn['id'] in used_connector_ids:
                        continue
                    name_lower = connector_name.lower()
                    if is_blocked(name_lower):
                        continue
                    if any(keyword in name_lower for keyword in bank_cfg['keywords']):
                        matches.append(conn)

                if not matches:
                    continue

                # Ordena priorizando conta corrente antes de cartões
                def sort_key(connector: dict) -> tuple:
                    name_lower = (connector.get('name') or '').lower()
                    is_card = 1 if "cart" in name_lower else 0
                    return (is_card, connector.get('name', ''))

                matches.sort(key=sort_key)

                for match in matches:
                    used_connector_ids.add(match['id'])
                    selected_connectors.append(match)

            main_banks = selected_connectors

            if not main_banks:
                await update.message.reply_text(
                    "❌ Nenhum banco suportado está disponível agora."
                    " Tente novamente em alguns minutos."
                )
                return ConversationHandler.END

            # Criar teclado inline
            keyboard = []
            for bank in main_banks:
                display_name = bank.get('name', '').strip() or bank.get('name', '')
                keyboard.append([
                    InlineKeyboardButton(
                        display_name,
                        callback_data=f"bank_{bank['id']}"
                    )
                ])

            keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="cancel")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            message = (
                "🏦 <b>Conectar Banco</b>\n\n"
                "Suportamos, por enquanto, apenas contas e cartões PF destes bancos:\n"
                "Inter, Itaú, Bradesco, Nubank, Caixa e Santander.\n\n"
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
            context.user_data['current_user_id'] = user_id
            
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

        # Preparar coleta sequencial das credenciais
        context.user_data['selected_connector'] = connector
        context.user_data['credential_fields'] = connector.get('credentials', [])
        context.user_data['collected_credentials'] = {}
        context.user_data['credential_index'] = 0
        context.user_data['ack_messages'] = []
        context.user_data['login_credentials'] = {}
        context.user_data['additional_credentials'] = {}
        context.user_data['current_phase'] = 'login'
        context.user_data['pending_item_id'] = None
        context.user_data['pending_connector_id'] = int(connector['id'])

        await query.edit_message_text(
            (
                f"🔐 <b>{connector['name']}</b> selecionado!\n\n"
                "Vou pedir cada informação em uma mensagem separada."
                " Assim consigo remover sua resposta para manter tudo seguro."
            ),
            parse_mode='HTML'
        )

        if not context.user_data['credential_fields']:
            # Alguns conectores não solicitam credenciais (ex.: dados públicos)
            return await self._finalize_connection(query.message.chat_id, context)

        return await self._prompt_next_field(query.message.chat_id, context)
    
    async def conectar_banco_credentials(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Recebe credenciais e cria conexão"""
        user_id = update.effective_user.id
        connector = context.user_data.get('selected_connector')
        
        if not connector:
            await update.message.reply_text("❌ Sessão expirada. Use /conectar_banco novamente.")
            return ConversationHandler.END
        
        fields = context.user_data.get('credential_fields', [])
        index = context.user_data.get('credential_index', 0)

        if not connector or index > len(fields):
            await update.message.reply_text("❌ Sessão expirada. Use /conectar_banco novamente.")
            context.user_data.clear()
            return ConversationHandler.END

        # Se já coletamos tudo, finalizar
        if index == len(fields):
            return await self._finalize_connection(update.message.chat_id, context)

        field = fields[index]
        raw_value = update.message.text.strip()

        try:
            value = self._sanitize_credential_input(field, raw_value)
        except ValueError as err:
            await update.message.reply_text(f"❌ {err}\nTente novamente.")
            try:
                await update.message.delete()
            except Exception:
                pass
            return ENTERING_FIELD

        field_name = field.get('name') or re.sub(r'\W+', '_', field.get('label', 'campo')).strip('_') or f'field_{index}'
        context.user_data['collected_credentials'][field_name] = value
        context.user_data['credential_index'] = index + 1

        phase = context.user_data.get('current_phase', 'login')
        if phase == 'login':
            context.user_data.setdefault('login_credentials', {})[field_name] = value
        else:
            context.user_data.setdefault('additional_credentials', {})[field_name] = value

        # Remover mensagem original por segurança
        try:
            await update.message.delete()
        except Exception:
            pass

        # Breve confirmação (removida em seguida)
        ack = await context.bot.send_message(
            chat_id=update.message.chat_id,
            text="🔒 Informação recebida e removida da conversa.",
            reply_markup=ReplyKeyboardRemove()
        )
        context.user_data['ack_messages'].append(ack.message_id)
        await asyncio.sleep(1.5)
        try:
            await context.bot.delete_message(update.message.chat_id, ack.message_id)
        except Exception:
            pass

        return await self._prompt_next_field(update.message.chat_id, context)
    
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
                ENTERING_FIELD: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.conectar_banco_credentials)
                ]
            },
            fallbacks=[CommandHandler('cancelar', self.cancel_conversation)]
        )
        
        return [
            connect_handler,
            CommandHandler('minhas_contas', self.minhas_contas),
            CommandHandler('saldo', self.saldo),
            CommandHandler('extrato', self.extrato),
            CommandHandler('desconectar_banco', self.desconectar_banco),
            CallbackQueryHandler(self.desconectar_banco_confirm, pattern='^disconnect_')
        ]

    async def cancel_conversation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Permite ao usuário cancelar o fluxo de conexão com segurança."""
        chat = update.effective_chat
        if chat:
            await self._cleanup_sensitive_messages(chat.id, context)

        if update.message:
            await update.message.reply_text(
                "❌ Conexão cancelada. Nenhum dado foi salvo.",
                reply_markup=ReplyKeyboardRemove()
            )

        context.user_data.clear()
        return ConversationHandler.END

    async def _prompt_next_field(self, chat_id: int, context: ContextTypes.DEFAULT_TYPE):
        """Pede o próximo campo de credencial necessário."""
        fields = context.user_data.get('credential_fields', [])
        index = context.user_data.get('credential_index', 0)

        if index >= len(fields):
            phase = context.user_data.get('current_phase', 'login')
            if phase == 'login':
                return await self._finalize_connection(chat_id, context)
            return await self._continue_connection(chat_id, context)

        field = fields[index]
        label = field.get('label') or field.get('name', 'Informação')
        label_fmt = label.strip().rstrip(':') or 'Informação'
        hint = field.get('hint') or ''

        instructions = [
            f"🔐 <b>{label_fmt}</b>",
            "Envie a informação agora. Eu removo sua mensagem assim que receber."
        ]

        if hint:
            instructions.append(f"<i>{hint}</i>")

        message = "\n".join(instructions)

        placeholder = field.get('placeholder') or label_fmt

        await context.bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode='HTML',
            reply_markup=ForceReply(selective=True, input_field_placeholder=placeholder)
        )

        return ENTERING_FIELD

    def _sanitize_credential_input(self, field: dict, value: str) -> str:
        """Normaliza e valida a entrada de credenciais antes do envio."""
        if not value:
            raise ValueError("Esse campo não pode ficar vazio.")

        name = (field.get('name') or '').lower()
        label = (field.get('label') or '').lower()
        field_type = (field.get('type') or '').lower()

        normalized = value.strip()

        if 'cpf' in name or 'cpf' in label:
            digits = re.sub(r'\D', '', normalized)
            if len(digits) != 11:
                raise ValueError("CPF deve ter 11 dígitos.")
            return digits

        if 'cnpj' in name or 'cnpj' in label:
            digits = re.sub(r'\D', '', normalized)
            if len(digits) != 14:
                raise ValueError("CNPJ deve ter 14 dígitos.")
            return digits

        if any(keyword in name for keyword in ('agencia', 'agência', 'agenc', 'branch')) or field_type == 'number':
            digits = re.sub(r'\D', '', normalized)
            if not digits:
                raise ValueError("Informe apenas números.")
            return digits

        if 'password' in name or 'senha' in name or 'password' in label or 'senha' in label:
            if len(normalized) < 4:
                raise ValueError("Senha muito curta.")
            return normalized

        return normalized

    async def _finalize_connection(self, chat_id: int, context: ContextTypes.DEFAULT_TYPE):
        """Cria a conexão no Pluggy e sincroniza as informações."""
        connector = context.user_data.get('selected_connector')
        user_id = context.user_data.get('current_user_id')
        credentials = context.user_data.get('login_credentials', {})

        if not connector or not user_id:
            await context.bot.send_message(chat_id, "❌ Sessão expirada. Use /conectar_banco novamente.")
            context.user_data.clear()
            return ConversationHandler.END

        await self._cleanup_sensitive_messages(chat_id, context)

        processing_msg = await context.bot.send_message(
            chat_id=chat_id,
            text="⏳ Conectando com o banco... Isso pode levar alguns segundos."
        )

        try:
            connection = await asyncio.to_thread(
                self.connector.create_connection,
                user_id=user_id,
                connector_id=int(connector['id']),
                credentials=credentials
            )

            await asyncio.to_thread(self.connector.sync_transactions, connection['id'], 30)

            accounts = await asyncio.to_thread(self.connector.list_accounts, user_id)

            created_at = connection.get('created_at')
            if isinstance(created_at, datetime):
                created_str = created_at.strftime('%d/%m/%Y %H:%M')
            else:
                created_str = str(created_at) if created_at else datetime.now().strftime('%d/%m/%Y %H:%M')

            if accounts:
                first_account = accounts[0]
                bank_name = first_account.get('bank_name') or connector.get('name')
                account_label = first_account.get('account_name') or first_account.get('type') or 'Conta'
                balance = format_currency(first_account.get('balance', 0))

                success_message = (
                    "✅ <b>Banco conectado com sucesso!</b>\n\n"
                    f"🏦 {bank_name}\n"
                    f"📅 {created_str}\n"
                    f"💳 {account_label}\n"
                    f"💰 Saldo: <b>{balance}</b>\n\n"
                    "Use /minhas_contas para ver todas as contas conectadas.\n"
                    "Use /extrato para ver suas transações."
                )
            else:
                status_info = await asyncio.to_thread(
                    self.connector.get_item_status,
                    connection.get('item_id')
                )
                status_detail = status_info.get('statusDetail') if isinstance(status_info, dict) else None
                detail_message = status_detail or (
                    "O banco informou que ainda está processando seus dados."
                )
                success_message = (
                    "⚠️ Conexão recebida, mas nenhuma conta foi liberada ainda.\n\n"
                    f"Status informado pela instituição: {detail_message}\n\n"
                    "Abra o app ou internet banking para confirmar a autorização e tente novamente em alguns minutos."
                )

            await processing_msg.edit_text(success_message, parse_mode='HTML')

            context.user_data.clear()
            return ConversationHandler.END

        except BankConnectorAdditionalAuthRequired as action_err:
            form_items = []
            if isinstance(action_err.form, dict):
                form_items = action_err.form.get('items') or []

            if form_items:
                logger.warning("Banco solicitou formulário adicional de autenticação")
                context.user_data['current_phase'] = 'additional'
                context.user_data['credential_fields'] = form_items
                context.user_data['credential_index'] = 0
                context.user_data['pending_item_id'] = action_err.item.get('id')
                context.user_data['pending_connector_id'] = int(connector['id'])
                context.user_data['additional_credentials'] = {}
                context.user_data['collected_credentials'] = {}
                context.user_data['ack_messages'] = []

                insights_msg = action_err.insights.get('providerMessage') if isinstance(action_err.insights, dict) else None
                next_step = action_err.next_step if isinstance(action_err.next_step, str) else None
                info_parts = [action_err.args[0]] if action_err.args else []
                if insights_msg and insights_msg not in info_parts:
                    info_parts.append(insights_msg)
                if next_step and next_step not in info_parts:
                    info_parts.append(f"Próximo passo: {next_step}")

                await processing_msg.edit_text(
                    "⚠️ " + "\n".join(filter(None, info_parts)) + "\n\n"
                    "Vou pedir as informações extras agora.",
                    parse_mode='HTML'
                )
                return await self._prompt_next_field(chat_id, context)

            logger.warning("Banco solicitou ação adicional sem formulário específico")
            await processing_msg.edit_text(
                "⚠️ O banco pediu uma confirmação adicional.\n"
                f"{action_err.args[0] if action_err.args else ''}"
            )
            context.user_data.clear()
            return ConversationHandler.END

        except BankConnectorUserActionRequired as action_err:
            logger.warning("Banco solicitou ação adicional do usuário")
            await processing_msg.edit_text(
                "⚠️ O banco pediu uma confirmação adicional.\n"
                f"{action_err.args[0]}"
            )
            context.user_data.clear()
            return ConversationHandler.END
        except BankConnectorTimeout as timeout_err:
            logger.warning("Tempo esgotado aguardando retorno do banco")
            await processing_msg.edit_text(
                "⏱️ A instituição ainda não liberou a conexão."
                f"\n{timeout_err}"
            )
            context.user_data.clear()
            return ConversationHandler.END
        except BankConnectorError as connector_err:
            logger.error(f"Erro do banco ao finalizar conexão: {connector_err}")
            await processing_msg.edit_text(
                "❌ O banco recusou o acesso. Verifique as credenciais ou tente novamente mais tarde."
                f"\nDetalhe: {connector_err}"
            )
            context.user_data.clear()
            return ConversationHandler.END
        except Exception:
            logger.exception("Erro ao finalizar conexão")
            await processing_msg.edit_text(
                "❌ Não foi possível conectar. Verifique as credenciais e tente novamente.")
            context.user_data.clear()
            return ConversationHandler.END

    async def _cleanup_sensitive_messages(self, chat_id: int, context: ContextTypes.DEFAULT_TYPE):
        """Remove mensagens auxiliares que possam conter IDs."""
        ack_messages = context.user_data.get('ack_messages', [])
        for message_id in ack_messages:
            try:
                await context.bot.delete_message(chat_id, message_id)
            except Exception:
                pass
        context.user_data['ack_messages'] = []

    async def _continue_connection(self, chat_id: int, context: ContextTypes.DEFAULT_TYPE):
        """Envio de credenciais adicionais (OTP/token) para concluir a conexão."""

        connector = context.user_data.get('selected_connector')
        user_id = context.user_data.get('current_user_id')
        item_id = context.user_data.get('pending_item_id')
        connector_id = context.user_data.get('pending_connector_id')
        login_credentials = context.user_data.get('login_credentials', {})
        additional_credentials = context.user_data.get('additional_credentials', {})

        if not all([connector, user_id, item_id, connector_id]):
            await context.bot.send_message(chat_id, "❌ Sessão expirada. Use /conectar_banco novamente.")
            context.user_data.clear()
            return ConversationHandler.END

        await self._cleanup_sensitive_messages(chat_id, context)

        processing_msg = await context.bot.send_message(
            chat_id=chat_id,
            text="⏳ Validando as informações adicionais..."
        )

        try:
            connection = await asyncio.to_thread(
                self.connector.resume_connection,
                user_id=user_id,
                connector_id=connector_id,
                item_id=item_id,
                login_credentials=login_credentials,
                additional_credentials=additional_credentials,
            )

            await asyncio.to_thread(self.connector.sync_transactions, connection['id'], 30)
            accounts = await asyncio.to_thread(self.connector.list_accounts, user_id)

            created_at = connection.get('created_at')
            created_str = (
                created_at.strftime('%d/%m/%Y %H:%M')
                if isinstance(created_at, datetime)
                else datetime.now().strftime('%d/%m/%Y %H:%M')
            )

            if accounts:
                first_account = accounts[0]
                bank_name = first_account.get('bank_name') or connector.get('name')
                account_label = first_account.get('account_name') or first_account.get('type') or 'Conta'
                balance = format_currency(first_account.get('balance', 0))
                message = (
                    "✅ <b>Banco conectado com sucesso!</b>\n\n"
                    f"🏦 {bank_name}\n"
                    f"📅 {created_str}\n"
                    f"💳 {account_label}\n"
                    f"💰 Saldo: <b>{balance}</b>\n\n"
                    "Use /minhas_contas para ver todas as contas conectadas.\n"
                    "Use /extrato para ver suas transações."
                )
            else:
                status_detail = connection.get('status_detail') or "O banco ainda está processando seus dados."
                message = (
                    "⚠️ Conexão recebida, mas nenhuma conta foi liberada ainda.\n\n"
                    f"Status informado pela instituição: {status_detail}\n\n"
                    "Abra o app ou internet banking para confirmar a autorização e tente novamente em alguns minutos."
                )

            await processing_msg.edit_text(message, parse_mode='HTML')

            context.user_data.clear()
            return ConversationHandler.END

        except BankConnectorAdditionalAuthRequired as action_err:
            form_items = []
            if isinstance(action_err.form, dict):
                form_items = action_err.form.get('items') or []

            if form_items:
                logger.warning("Banco solicitou nova rodada de credenciais adicionais")
                context.user_data['credential_fields'] = form_items
                context.user_data['credential_index'] = 0
                context.user_data['pending_item_id'] = action_err.item.get('id')
                context.user_data['additional_credentials'] = {}
                context.user_data['collected_credentials'] = {}
                context.user_data['ack_messages'] = []

                insights_msg = action_err.insights.get('providerMessage') if isinstance(action_err.insights, dict) else None
                info_parts = [action_err.args[0]] if action_err.args else []
                if insights_msg and insights_msg not in info_parts:
                    info_parts.append(insights_msg)

                await processing_msg.edit_text(
                    "⚠️ " + "\n".join(filter(None, info_parts)) + "\n\n"
                    "Preciso de mais informações. Me envie conforme solicitado.",
                    parse_mode='HTML'
                )
                return await self._prompt_next_field(chat_id, context)

            await processing_msg.edit_text(
                "⚠️ O banco ainda está aguardando uma confirmação adicional."
            )
            context.user_data.clear()
            return ConversationHandler.END

        except BankConnectorUserActionRequired as action_err:
            logger.warning("Banco ainda requer ação manual do usuário")
            await processing_msg.edit_text(
                "⚠️ O banco pediu uma confirmação adicional.\n"
                f"{action_err.args[0]}"
            )
            context.user_data.clear()
            return ConversationHandler.END

        except BankConnectorTimeout as timeout_err:
            logger.warning("Tempo esgotado aguardando retorno do banco (etapa adicional)")
            await processing_msg.edit_text(
                "⏱️ A instituição ainda não liberou a conexão."
                f"\n{timeout_err}"
            )
            context.user_data.clear()
            return ConversationHandler.END

        except BankConnectorError as connector_err:
            logger.error(f"Erro do banco ao concluir conexão com dados adicionais: {connector_err}")
            await processing_msg.edit_text(
                "❌ O banco recusou o acesso. Verifique as informações e tente novamente."
                f"\nDetalhe: {connector_err}"
            )
            context.user_data.clear()
            return ConversationHandler.END

        except Exception:
            logger.exception("Erro ao finalizar conexão com dados adicionais")
            await processing_msg.edit_text(
                "❌ Não foi possível conectar. Verifique as credenciais e tente novamente.")
            context.user_data.clear()
            return ConversationHandler.END
