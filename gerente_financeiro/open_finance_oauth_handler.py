"""
🔐 Handler Open Finance OAuth - Telegram Bot
Gerencia conexões bancárias via OAuth/Open Finance (substitui handler antigo)
"""

import asyncio
import logging
import os
import re
import requests
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters
)

logger = logging.getLogger(__name__)

# Estados da conversa
SELECTING_BANK, ENTERING_CPF, WAITING_AUTH = range(3)

# Configuração Pluggy
PLUGGY_CLIENT_ID = os.getenv("PLUGGY_CLIENT_ID")
PLUGGY_CLIENT_SECRET = os.getenv("PLUGGY_CLIENT_SECRET")
PLUGGY_BASE_URL = "https://api.pluggy.ai"

# Cache de API Key
_api_key_cache = {"key": None, "expires_at": None}


def get_pluggy_api_key() -> str:
    """Obtém API Key da Pluggy (com cache de 23h)"""
    now = datetime.now()
    
    if _api_key_cache["key"] and _api_key_cache["expires_at"] and now < _api_key_cache["expires_at"]:
        return _api_key_cache["key"]
    
    logger.info("🔑 Obtendo nova API Key da Pluggy...")
    
    response = requests.post(
        f"{PLUGGY_BASE_URL}/auth",
        json={"clientId": PLUGGY_CLIENT_ID, "clientSecret": PLUGGY_CLIENT_SECRET},
        headers={"Content-Type": "application/json"},
        timeout=30
    )
    response.raise_for_status()
    
    _api_key_cache["key"] = response.json()["apiKey"]
    _api_key_cache["expires_at"] = now + timedelta(hours=23)
    
    logger.info("✅ API Key obtida com sucesso")
    return _api_key_cache["key"]


def pluggy_request(method: str, endpoint: str, data: Optional[Dict] = None, params: Optional[Dict] = None) -> Dict:
    """Faz requisição autenticada à API Pluggy"""
    api_key = get_pluggy_api_key()
    
    url = f"{PLUGGY_BASE_URL}{endpoint}"
    headers = {
        "X-API-KEY": api_key,
        "Content-Type": "application/json"
    }
    
    response = requests.request(
        method=method,
        url=url,
        json=data,
        params=params,
        headers=headers,
        timeout=30
    )
    response.raise_for_status()
    return response.json()


# ==================== PERSISTÊNCIA NO BANCO ====================

def save_pluggy_item_to_db(user_id: int, item_data: Dict, connector_data: Dict) -> bool:
    """
    Salva ou atualiza PluggyItem no banco de dados.
    
    Args:
        user_id: Telegram ID do usuário
        item_data: Dados do item retornados pela API Pluggy
        connector_data: Dados do conector (banco) usado
    
    Returns:
        True se salvou com sucesso, False caso contrário
    """
    try:
        from database.database import get_db
        from models import Usuario, PluggyItem
        
        db = next(get_db())
        
        # Buscar usuário
        usuario = db.query(Usuario).filter(Usuario.telegram_id == user_id).first()
        if not usuario:
            logger.error(f"❌ Usuário {user_id} não encontrado no banco")
            return False
        
        # Verificar se item já existe
        existing_item = db.query(PluggyItem).filter(
            PluggyItem.pluggy_item_id == item_data["id"]
        ).first()
        
        if existing_item:
            # Atualizar item existente
            existing_item.status = item_data.get("status", "UNKNOWN")
            existing_item.status_detail = item_data.get("statusDetail")
            existing_item.execution_status = item_data.get("executionStatus")
            existing_item.last_updated_at = datetime.now()
            existing_item.updated_at = datetime.now()
            
            logger.info(f"🔄 Item {item_data['id']} atualizado no banco")
        else:
            # Criar novo item
            new_item = PluggyItem(
                id_usuario=usuario.id,
                pluggy_item_id=item_data["id"],
                connector_id=connector_data["id"],
                connector_name=connector_data["name"],
                status=item_data.get("status", "UNKNOWN"),
                status_detail=item_data.get("statusDetail"),
                execution_status=item_data.get("executionStatus"),
                last_updated_at=datetime.now() if item_data.get("status") in ("UPDATED", "PARTIAL_SUCCESS") else None
            )
            
            db.add(new_item)
            logger.info(f"✅ Item {item_data['id']} ({connector_data['name']}) salvo no banco")
        
        db.commit()
        
        # Buscar e salvar accounts
        save_pluggy_accounts_to_db(item_data["id"])
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao salvar PluggyItem no banco: {e}", exc_info=True)
        return False
    finally:
        db.close()


def save_pluggy_accounts_to_db(item_id: str) -> bool:
    """
    Busca accounts do item na API Pluggy e salva no banco.
    
    Args:
        item_id: ID do item na Pluggy
    
    Returns:
        True se salvou com sucesso, False caso contrário
    """
    try:
        from database.database import get_db
        from models import PluggyItem, PluggyAccount
        
        # Buscar accounts na API Pluggy
        accounts_data = pluggy_request("GET", f"/accounts", params={"itemId": item_id})
        accounts = accounts_data.get("results", [])
        
        if not accounts:
            logger.info(f"ℹ️  Nenhuma account encontrada para item {item_id}")
            return True
        
        db = next(get_db())
        
        # Buscar PluggyItem no banco
        pluggy_item = db.query(PluggyItem).filter(
            PluggyItem.pluggy_item_id == item_id
        ).first()
        
        if not pluggy_item:
            logger.error(f"❌ PluggyItem {item_id} não encontrado no banco")
            return False
        
        saved_count = 0
        for account in accounts:
            # Verificar se account já existe
            existing_account = db.query(PluggyAccount).filter(
                PluggyAccount.pluggy_account_id == account["id"]
            ).first()
            
            if existing_account:
                # Atualizar account existente
                existing_account.balance = account.get("balance")
                existing_account.credit_limit = account.get("creditLimit")
                existing_account.updated_at = datetime.now()
                logger.info(f"🔄 Account {account['id']} atualizada")
            else:
                # Criar nova account
                new_account = PluggyAccount(
                    id_item=pluggy_item.id,
                    pluggy_account_id=account["id"],
                    type=account.get("type", "BANK"),
                    subtype=account.get("subtype"),
                    number=account.get("number"),
                    name=account.get("name", "Conta"),
                    balance=account.get("balance"),
                    currency_code=account.get("currencyCode", "BRL"),
                    credit_limit=account.get("creditLimit")
                )
                
                db.add(new_account)
                saved_count += 1
                logger.info(f"✅ Account {account['id']} ({account.get('name')}) salva")
        
        db.commit()
        logger.info(f"💾 {saved_count} account(s) salva(s) para item {item_id}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao salvar PluggyAccounts: {e}", exc_info=True)
        return False
    finally:
        db.close()


class OpenFinanceOAuthHandler:
    """Handler para Open Finance com OAuth"""
    
    def __init__(self):
        self.active_connections: Dict[int, Dict] = {}  # user_id -> connection_data
    
    # ==================== /conectar_banco ====================
    
    async def conectar_banco_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Inicia processo de conexão Open Finance"""
        user_id = update.effective_user.id
        
        logger.info(f"👤 Usuário {user_id} iniciando conexão Open Finance")
        
        await update.message.reply_text(
            "🏦 *Conectar Banco via Open Finance*\n\n"
            "Vou listar os bancos disponíveis...",
            parse_mode="Markdown"
        )
        
        try:
            # Listar conectores OAuth
            result = pluggy_request("GET", "/connectors", params={"countries": "BR"})
            all_connectors = result.get("results", [])
            
            # Filtrar apenas OAuth e bancos pessoais/empresariais
            oauth_connectors = [
                c for c in all_connectors 
                if c.get("oauth", False) and c.get("type") in ("PERSONAL_BANK", "BUSINESS_BANK")
            ]
            
            if not oauth_connectors:
                await update.message.reply_text(
                    "❌ Nenhum banco com Open Finance disponível no momento.\n"
                    "Tente novamente mais tarde."
                )
                return ConversationHandler.END
            
            # Ordenar por nome
            oauth_connectors.sort(key=lambda x: x["name"])
            
            # Bancos obrigatórios (principais do Brasil)
            priority_banks = [
                "Nubank", "Inter", "Bradesco", "Itaú", "Itau", "Santander", 
                "Mercado Pago", "XP", "Banco do Brasil", "Caixa"
            ]
            
            # Separar bancos principais dos outros
            priority = []
            others = []
            
            for conn in oauth_connectors:
                name = conn["name"]
                if any(bank.lower() in name.lower() for bank in priority_banks):
                    priority.append(conn)
                else:
                    others.append(conn)
            
            # Ordenar prioridade por ordem da lista priority_banks
            def get_priority_index(conn):
                name_lower = conn["name"].lower()
                for idx, bank in enumerate(priority_banks):
                    if bank.lower() in name_lower:
                        return idx
                return 999
            
            priority.sort(key=get_priority_index)
            
            # Mostrar APENAS bancos prioritários (sem "outros")
            display_connectors = priority[:20]  # Máximo 20 bancos principais
            
            # Criar teclado inline
            keyboard = []
            for conn in display_connectors:
                keyboard.append([
                    InlineKeyboardButton(
                        f"🏦 {conn['name']}", 
                        callback_data=f"of_bank_{conn['id']}"
                    )
                ])
            
            keyboard.append([
                InlineKeyboardButton("❌ Cancelar", callback_data="of_cancel")
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"🏦 *Escolha seu banco*\n\n"
                f"✅ {len(display_connectors)} bancos disponíveis\n"
                f"🔒 Conexão segura via Open Finance\n\n"
                f"Selecione o banco abaixo:",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            
            # Salvar lista no contexto
            context.user_data["of_connectors"] = {c["id"]: c for c in oauth_connectors}
            
            return SELECTING_BANK
            
        except Exception as e:
            logger.error(f"❌ Erro ao listar bancos: {e}")
            await update.message.reply_text(
                "❌ Erro ao buscar bancos disponíveis.\n"
                "Tente novamente em alguns instantes."
            )
            return ConversationHandler.END
    
    async def conectar_banco_selected(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Banco selecionado - pedir CPF"""
        query = update.callback_query
        await query.answer()
        
        if query.data == "of_cancel":
            await query.edit_message_text("❌ Conexão cancelada.")
            return ConversationHandler.END
        
        connector_id = int(query.data.split("_")[-1])
        connectors = context.user_data.get("of_connectors", {})
        connector = connectors.get(connector_id)
        
        if not connector:
            await query.edit_message_text("❌ Banco não encontrado. Tente novamente.")
            return ConversationHandler.END
        
        # Salvar banco escolhido
        context.user_data["of_selected_bank"] = connector
        
        # Verificar credenciais necessárias
        credentials = connector.get("credentials", [])
        cpf_field = next((c for c in credentials if c["name"] == "cpf"), None)
        
        if not cpf_field:
            await query.edit_message_text(
                f"❌ {connector['name']} não requer CPF.\n"
                "Este fluxo suporta apenas bancos que usam CPF."
            )
            return ConversationHandler.END
        
        await query.edit_message_text(
            f"🏦 *{connector['name']}*\n\n"
            f"📝 Digite seu CPF (apenas números):",
            parse_mode="Markdown"
        )
        
        return ENTERING_CPF
    
    async def conectar_banco_cpf(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """CPF informado - criar item e gerar OAuth URL"""
        user_id = update.effective_user.id
        cpf = update.message.text.strip().replace(".", "").replace("-", "")
        
        # Validar CPF (apenas formato)
        if not cpf.isdigit() or len(cpf) != 11:
            await update.message.reply_text(
                "❌ CPF inválido. Digite apenas os 11 números."
            )
            return ENTERING_CPF
        
        connector = context.user_data.get("of_selected_bank")
        if not connector:
            await update.message.reply_text("❌ Erro: banco não selecionado.")
            return ConversationHandler.END
        
        # Deletar mensagem com CPF (segurança)
        try:
            await update.message.delete()
        except:
            pass
        
        status_msg = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"🔄 Criando conexão com *{connector['name']}*...",
            parse_mode="Markdown"
        )
        
        try:
            # Criar item na Pluggy
            item_data = {
                "connectorId": connector["id"],
                "parameters": {"cpf": cpf}
            }
            
            item = pluggy_request("POST", "/items", data=item_data)
            item_id = item["id"]
            
            logger.info(f"✅ Item criado: {item_id} para usuário {user_id}")
            
            # Salvar item no contexto
            context.user_data["of_item_id"] = item_id
            context.user_data["of_item_status"] = item.get("status")
            
            # Salvar connector data para persistência futura
            self.active_connections[user_id] = {
                "item_id": item_id,
                "connector": connector,
                "created_at": datetime.now()
            }
            
            # Aguardar alguns segundos para API processar
            await asyncio.sleep(3)
            
            # Consultar item novamente para pegar URL OAuth
            item_updated = pluggy_request("GET", f"/items/{item_id}")
            
            # Procurar URL OAuth
            oauth_url = None
            parameter = item_updated.get("parameter", {})
            
            if parameter and parameter.get("type") == "oauth" and parameter.get("data"):
                oauth_url = parameter["data"]
            
            if not oauth_url:
                # Tentar em userAction
                user_action = item_updated.get("userAction")
                if user_action and user_action.get("url"):
                    oauth_url = user_action["url"]
            
            if oauth_url:
                # Criar botão inline com URL
                keyboard = [
                    [InlineKeyboardButton("🔐 Autorizar no Banco", url=oauth_url)],
                    [InlineKeyboardButton("✅ Já Autorizei", callback_data=f"of_authorized_{item_id}")],
                    [InlineKeyboardButton("❌ Cancelar", callback_data="of_cancel_auth")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await status_msg.edit_text(
                    f"🔐 *Autorização Necessária*\n\n"
                    f"🏦 Banco: *{connector['name']}*\n"
                    f"🆔 Conexão: `{item_id}`\n\n"
                    f"👉 Clique no botão abaixo para autorizar o acesso:\n\n"
                    f"⚠️ Você será redirecionado para o site oficial do banco.\n"
                    f"✅ Após autorizar, clique em *'Já Autorizei'*.",
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )
                
                # Iniciar polling em background
                asyncio.create_task(
                    self._poll_item_status(user_id, item_id, connector["name"], context)
                )
                
                return WAITING_AUTH
                
            else:
                # Sem OAuth URL - pode ser erro ou banco que não precisa
                status = item_updated.get("status")
                
                if status in ("UPDATED", "PARTIAL_SUCCESS"):
                    await status_msg.edit_text(
                        f"✅ *Banco conectado!*\n\n"
                        f"🏦 {connector['name']}\n"
                        f"✅ Status: {status}\n\n"
                        f"Use /minhas_contas para ver suas contas."
                    )
                    return ConversationHandler.END
                else:
                    await status_msg.edit_text(
                        f"⚠️ *Aguardando processamento*\n\n"
                        f"🏦 {connector['name']}\n"
                        f"Status: {status}\n\n"
                        f"Vou te avisar quando estiver pronto!"
                    )
                    
                    # Polling em background
                    asyncio.create_task(
                        self._poll_item_status(user_id, item_id, connector["name"], context)
                    )
                    
                    return ConversationHandler.END
                    
        except Exception as e:
            logger.error(f"❌ Erro ao criar item: {e}")
            await status_msg.edit_text(
                f"❌ *Erro ao conectar*\n\n"
                f"Não foi possível criar a conexão com {connector['name']}.\n\n"
                f"Erro: {str(e)}"
            )
            return ConversationHandler.END
    
    async def conectar_banco_authorized(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Usuário clicou em 'Já Autorizei'"""
        query = update.callback_query
        await query.answer("🔄 Verificando autorização...")
        
        if query.data == "of_cancel_auth":
            await query.edit_message_text("❌ Autorização cancelada.")
            return ConversationHandler.END
        
        item_id = query.data.split("_")[-1]
        
        try:
            # Consultar status do item
            item = pluggy_request("GET", f"/items/{item_id}")
            status = item.get("status")
            
            if status in ("UPDATED", "PARTIAL_SUCCESS"):
                connector_name = item.get("connector", {}).get("name", "Banco")
                
                await query.edit_message_text(
                    f"✅ *Banco conectado com sucesso!*\n\n"
                    f"🏦 {connector_name}\n"
                    f"✅ Status: {status}\n\n"
                    f"Use /minhas_contas para ver suas contas.",
                    parse_mode="Markdown"
                )
                return ConversationHandler.END
                
            elif status == "WAITING_USER_INPUT":
                await query.answer("⏳ Ainda aguardando autorização...", show_alert=True)
                return WAITING_AUTH
                
            else:
                await query.edit_message_text(
                    f"⏳ *Processando...*\n\n"
                    f"Status atual: {status}\n\n"
                    f"Vou te avisar quando estiver pronto!",
                    parse_mode="Markdown"
                )
                return ConversationHandler.END
                
        except Exception as e:
            logger.error(f"❌ Erro ao verificar status: {e}")
            await query.edit_message_text(
                f"❌ Erro ao verificar status da conexão.\n\n{str(e)}"
            )
            return ConversationHandler.END
    
    # ==================== /minhas_contas ====================
    
    async def minhas_contas(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Lista contas bancárias conectadas via Open Finance"""
        user_id = update.effective_user.id
        
        logger.info(f"👤 Usuário {user_id} consultando contas Open Finance")
        
        try:
            from database.database import get_db
            from models import Usuario, PluggyItem, PluggyAccount
            
            db = next(get_db())
            
            # Buscar usuário
            usuario = db.query(Usuario).filter(Usuario.telegram_id == user_id).first()
            if not usuario:
                await update.message.reply_text(
                    "❌ Usuário não encontrado.\n"
                    "Use /start para criar sua conta."
                )
                return
            
            # Buscar items do usuário
            items = db.query(PluggyItem).filter(
                PluggyItem.id_usuario == usuario.id
            ).order_by(PluggyItem.created_at.desc()).all()
            
            if not items:
                await update.message.reply_text(
                    "🏦 *Nenhuma conta conectada*\n\n"
                    "Você ainda não conectou nenhum banco via Open Finance\\.\n\n"
                    "Use /conectar\\_banco para conectar\\.",
                    parse_mode="MarkdownV2"
                )
                return
            
            # Montar mensagem com todas as contas
            message = "🏦 *Suas Contas Open Finance*\n\n"
            
            for item in items:
                # Status do item
                status_emoji = {
                    "UPDATED": "✅",
                    "UPDATING": "🔄",
                    "LOGIN_ERROR": "❌",
                    "ERROR": "❌",
                    "PARTIAL_SUCCESS": "⚠️"
                }.get(item.status, "❓")
                
                # Escapar caracteres especiais
                safe_bank = item.connector_name.replace("_", "\\_").replace("*", "\\*").replace("[", "\\[")
                safe_status = item.status.replace("_", "\\_")
                
                message += f"{status_emoji} *{safe_bank}*\n"
                message += f"   Status: `{safe_status}`\n"
                
                # Buscar accounts deste item
                accounts = db.query(PluggyAccount).filter(
                    PluggyAccount.id_item == item.id
                ).all()
                
                if accounts:
                    for acc in accounts:
                        # Tipo de conta
                        type_emoji = {
                            "BANK": "🏦",
                            "CREDIT": "💳",
                            "INVESTMENT": "📈"
                        }.get(acc.type, "💰")
                        
                        safe_acc_name = acc.name.replace("_", "\\_").replace("*", "\\*").replace("[", "\\[")
                        
                        message += f"   {type_emoji} {safe_acc_name}\n"
                        
                        if acc.balance is not None:
                            balance_str = f"R$ {float(acc.balance):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                            message += f"      Saldo: `{balance_str}`\n"
                        
                        if acc.credit_limit is not None:
                            limit_str = f"R$ {float(acc.credit_limit):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                            message += f"      Limite: `{limit_str}`\n"
                else:
                    message += "   ℹ️  Nenhuma conta encontrada\n"
                
                message += "\n"
            
            message += "🔄 Use /conectar\\_banco para adicionar mais bancos\\.\n"
            message += "🗑️ Use /desconectar\\_banco para remover conexões\\."
            
            await update.message.reply_text(message, parse_mode="MarkdownV2")
            
        except Exception as e:
            logger.error(f"❌ Erro ao listar contas: {e}", exc_info=True)
            await update.message.reply_text(
                "❌ Erro ao buscar suas contas.\n"
                "Tente novamente em alguns instantes."
            )
        finally:
            db.close()
    
    async def cancel_conversation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancela a conversa"""
        if update.callback_query:
            await update.callback_query.edit_message_text("❌ Operação cancelada.")
        else:
            await update.message.reply_text("❌ Operação cancelada.")
        return ConversationHandler.END
    
    # ==================== POLLING STATUS ====================
    
    async def _poll_item_status(
        self, 
        user_id: int, 
        item_id: str, 
        bank_name: str,
        context: ContextTypes.DEFAULT_TYPE,
        max_attempts: int = 60
    ):
        """Faz polling do status do item em background"""
        logger.info(f"🔄 Iniciando polling para item {item_id}")
        
        attempt = 0
        while attempt < max_attempts:
            try:
                await asyncio.sleep(5)  # Aguardar 5 segundos entre tentativas
                
                item = pluggy_request("GET", f"/items/{item_id}")
                status = item.get("status")
                
                logger.info(f"📊 Polling item {item_id}: tentativa {attempt+1}/{max_attempts}, status={status}")
                
                # Status de sucesso
                if status in ("UPDATED", "PARTIAL_SUCCESS"):
                    # 💾 Salvar item e accounts no banco de dados
                    try:
                        # Buscar dados do conector (precisa estar salvo no contexto)
                        connector_data = self.active_connections.get(user_id, {}).get("connector")
                        if connector_data:
                            save_success = save_pluggy_item_to_db(user_id, item, connector_data)
                            if save_success:
                                logger.info(f"💾 Dados do item {item_id} salvos no banco")
                            else:
                                logger.warning(f"⚠️  Falha ao salvar dados do item {item_id} no banco")
                        else:
                            logger.warning(f"⚠️  Connector data não encontrada para salvar item {item_id}")
                    except Exception as save_error:
                        logger.error(f"❌ Erro ao salvar item no banco: {save_error}")
                        # Não falhar a conexão se salvar no banco falhar
                    
                    # Escapar caracteres especiais do Markdown
                    safe_bank_name = bank_name.replace("_", "\\_").replace("*", "\\*").replace("[", "\\[").replace("`", "\\`")
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=f"✅ *Banco conectado\\!*\n\n"
                             f"🏦 {safe_bank_name}\n"
                             f"✅ Sincronização concluída\n\n"
                             f"Use /minhas\\_contas para ver suas contas\\.",
                        parse_mode="MarkdownV2"
                    )
                    logger.info(f"✅ Item {item_id} conectado com sucesso")
                    break
                
                # Status de erro
                if status in ("LOGIN_ERROR", "INVALID_CREDENTIALS", "ERROR", "SUSPENDED"):
                    status_detail = item.get("statusDetail", "Erro desconhecido")
                    # Escapar caracteres especiais
                    safe_bank_name = bank_name.replace("_", "\\_").replace("*", "\\*").replace("[", "\\[").replace("`", "\\`")
                    safe_status = status.replace("_", "\\_")
                    safe_detail = status_detail.replace("_", "\\_").replace("*", "\\*").replace("[", "\\[")
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=f"❌ *Falha na conexão*\n\n"
                             f"🏦 {safe_bank_name}\n"
                             f"❌ Status: {safe_status}\n"
                             f"📝 Detalhes: {safe_detail}\n\n"
                             f"Tente novamente com /conectar\\_banco",
                        parse_mode="MarkdownV2"
                    )
                    logger.warning(f"❌ Item {item_id} falhou: {status}")
                    break
                
                attempt += 1
                
            except Exception as e:
                logger.error(f"❌ Erro no polling do item {item_id}: {e}")
                attempt += 1
        
        if attempt >= max_attempts:
            logger.warning(f"⏰ Timeout no polling do item {item_id}")
            try:
                safe_bank_name = bank_name.replace("_", "\\_").replace("*", "\\*").replace("[", "\\[").replace("`", "\\`")
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"⏰ *Timeout na conexão*\n\n"
                         f"🏦 {safe_bank_name}\n"
                         f"⏳ A sincronização está demorando mais que o esperado\\.\n\n"
                         f"Verifique /minhas\\_contas em alguns minutos\\.",
                    parse_mode="MarkdownV2"
                )
            except Exception as e:
                logger.error(f"❌ Erro ao enviar mensagem de timeout: {e}")
    
    # ==================== CONVERSATION HANDLER ====================
    
    def get_conversation_handler(self) -> ConversationHandler:
        """Retorna o ConversationHandler configurado"""
        return ConversationHandler(
            entry_points=[
                CommandHandler("conectar_banco", self.conectar_banco_start)
            ],
            states={
                SELECTING_BANK: [
                    CallbackQueryHandler(self.conectar_banco_selected)
                ],
                ENTERING_CPF: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.conectar_banco_cpf)
                ],
                WAITING_AUTH: [
                    CallbackQueryHandler(self.conectar_banco_authorized)
                ]
            },
            fallbacks=[
                CommandHandler("cancelar", self.cancel_conversation),
                CallbackQueryHandler(self.cancel_conversation, pattern="^of_cancel")
            ],
            name="open_finance_oauth_conversation",
            persistent=False
        )
