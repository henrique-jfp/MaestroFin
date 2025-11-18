"""
🔐 Handler Open Finance OAuth - Telegram Bot
Gerencia conexões bancárias via OAuth/Open Finance (substitui handler antigo)
"""

import asyncio
import json
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


def escape_markdown_v2(text: str) -> str:
    """
    Escapa caracteres especiais para MarkdownV2 do Telegram.
    
    Caracteres que precisam ser escapados: _*[]()~`>#+-=|{}.!
    """
    special_chars = r'_*[]()~`>#+-=|{}.!'
    return ''.join(f'\\{char}' if char in special_chars else char for char in text)

# Configuração Pluggy
PLUGGY_CLIENT_ID = os.getenv("PLUGGY_CLIENT_ID")
PLUGGY_CLIENT_SECRET = os.getenv("PLUGGY_CLIENT_SECRET")
PLUGGY_BASE_URL = "https://api.pluggy.ai"

# Cache de API Key
_api_key_cache = {"key": None, "expires_at": None}

# Cache de conexões pendentes por usuário (evitar múltiplas conexões simultâneas)
_pending_connections = {}  # {user_id: {"item_id": str, "timestamp": datetime, "connector_name": str}}


def _parse_transaction_date(date_string: Optional[str]) -> datetime.date:
    """
    Parse de data de transação da API Pluggy.
    Suporta formatos: 
    - ISO 8601 completo: "2025-11-15T19:29:37.000Z"
    - Apenas data: "2025-11-15"
    """
    if not date_string:
        return datetime.now().date()
    
    try:
        # Tenta ISO 8601 completo primeiro
        if "T" in date_string:
            # Remove milissegundos e timezone para simplificar
            date_string = date_string.split(".")[0].replace("Z", "")
            return datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%S").date()
        else:
            # Formato apenas data
            return datetime.strptime(date_string, "%Y-%m-%d").date()
    except Exception as e:
        logger.warning(f"⚠️ Erro ao fazer parse de data '{date_string}': {e}. Usando data atual.")
        return datetime.now().date()


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
    
    # Log detalhado em caso de erro
    if not response.ok:
        try:
            error_detail = response.json()
            logger.error(f"❌ Pluggy API Error {response.status_code}: {error_detail}")
        except:
            logger.error(f"❌ Pluggy API Error {response.status_code}: {response.text}")
    
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
            existing_item.status_detail = json.dumps(item_data.get("statusDetail")) if item_data.get("statusDetail") else None
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
                status_detail=json.dumps(item_data.get("statusDetail")) if item_data.get("statusDetail") else None,
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


def _sync_investments_from_accounts(pluggy_item_id: int, db, raw_accounts: List[Dict] = None) -> None:
    """
    Cria/atualiza registros de Investment para contas do tipo INVESTMENT.
    
    Args:
        pluggy_item_id: ID local do PluggyItem
        db: Sessão do banco de dados (já aberta)
        raw_accounts: Lista de contas cruas da API Pluggy (opcional, para acessar bankData)
    """
    try:
        from models import PluggyAccount, PluggyItem, Investment, InvestmentSnapshot, Usuario
        from datetime import date
        from decimal import Decimal
        
        # Buscar item para pegar id_usuario
        pluggy_item = db.query(PluggyItem).filter(PluggyItem.id == pluggy_item_id).first()
        if not pluggy_item:
            logger.warning(f"⚠️  PluggyItem {pluggy_item_id} não encontrado")
            return
        
        id_usuario = pluggy_item.id_usuario
        banco_nome = pluggy_item.connector_name
        
        # Buscar contas de investimento deste item
        all_accounts = db.query(PluggyAccount).filter(
            PluggyAccount.id_item == pluggy_item_id
        ).all()
        
        # Mapa de dados crus para acesso rápido
        raw_map = {acc["id"]: acc for acc in raw_accounts} if raw_accounts else {}
        
        # Filtrar contas que são investimentos
        # Aceitar: type=INVESTMENT OU nome contém "cofrinho" OU subtype indica investimento
        # OU possui transações de rendimento de aplicação financeira
        # OU possui automaticallyInvestedBalance > 0
        investment_accounts = []
        for acc in all_accounts:
            nome_lower = (acc.name or "").lower()
            subtype_lower = (acc.subtype or "").lower()
            
            # Verificar se tem transações de rendimento (indica investimento)
            has_rendimentos = False
            try:
                from models import PluggyTransaction
                rendimentos_count = db.query(PluggyTransaction).filter(
                    PluggyTransaction.id_account == acc.id,
                    PluggyTransaction.type == "CREDIT"
                ).filter(
                    (PluggyTransaction.category.ilike("%interest%")) |
                    (PluggyTransaction.category.ilike("%dividend%")) |
                    (PluggyTransaction.description.ilike("%rendimento%"))
                ).count()
                has_rendimentos = rendimentos_count > 0
            except Exception as e:
                logger.warning(f"⚠️ Erro ao verificar rendimentos: {e}")
            
            # Verificar automaticallyInvestedBalance nos dados crus
            is_remunerated = False
            raw_data = raw_map.get(acc.pluggy_account_id)
            if raw_data and "bankData" in raw_data and raw_data["bankData"]:
                auto_invested = raw_data["bankData"].get("automaticallyInvestedBalance", 0) or 0
                if float(auto_invested) > 0:
                    is_remunerated = True
            
            is_investment = (
                acc.type == "INVESTMENT" or
                "cofrinho" in nome_lower or
                "cofre" in nome_lower or
                "caixinha" in nome_lower or
                "investimento" in nome_lower or
                "investment" in subtype_lower or
                "savings" in subtype_lower or
                "poupança" in nome_lower or
                "poupanca" in nome_lower or
                has_rendimentos or
                is_remunerated
            )
            
            if is_investment:
                # Armazenar flag temporária no objeto para usar depois
                acc._is_remunerated = is_remunerated
                investment_accounts.append(acc)
                
                motivo = []
                if acc.type == "INVESTMENT": motivo.append("tipo=INVESTMENT")
                if "cofrinho" in nome_lower or "cofre" in nome_lower: motivo.append("nome contém cofrinho/cofre")
                if has_rendimentos: motivo.append("possui transações de rendimento")
                if is_remunerated: motivo.append("saldo automático investido")
                
                logger.info(f"💰 Detectado investimento: {acc.name} (tipo: {acc.type}, razão: {', '.join(motivo)})")
        
        if not investment_accounts:
            logger.info(f"ℹ️  Nenhuma conta de investimento encontrada para item {pluggy_item_id}")
            return
        
        logger.info(f"📈 Encontradas {len(investment_accounts)} conta(s) de investimento")
        
        for account in investment_accounts:
            # Tentar descobrir o tipo de investimento pelo nome/subtype
            tipo = _guess_investment_type(account.name, account.subtype)
            
            # Se for conta remunerada e caiu como OUTRO, ajustar
            if getattr(account, "_is_remunerated", False) and tipo == "OUTRO":
                tipo = "CONTA REMUNERADA"
            
            valor_atual = Decimal(account.balance) if account.balance else Decimal(0)
            
            # Verificar se já existe Investment para esta account
            existing_investment = db.query(Investment).filter(
                Investment.id_account == account.id
            ).first()
            
            if existing_investment:
                # Atualizar investment existente
                valor_anterior = existing_investment.valor_atual
                existing_investment.valor_atual = valor_atual
                existing_investment.updated_at = datetime.now()
                
                logger.info(f"🔄 Investment atualizado: {account.name} - R$ {float(valor_anterior):.2f} → R$ {float(valor_atual):.2f}")
                
                # Criar snapshot se valor mudou
                if valor_atual != valor_anterior:
                    rentabilidade = valor_atual - valor_anterior
                    rentabilidade_pct = (rentabilidade / valor_anterior * 100) if valor_anterior > 0 else 0
                    
                    snapshot = InvestmentSnapshot(
                        id_investment=existing_investment.id,
                        valor=valor_atual,
                        rentabilidade_periodo=rentabilidade,
                        rentabilidade_percentual=rentabilidade_pct,
                        data_snapshot=date.today()
                    )
                    db.add(snapshot)
                    logger.info(f"📊 Snapshot criado: {account.name} - Rent: R$ {float(rentabilidade):.2f} ({float(rentabilidade_pct):.2f}%)")
            else:
                # Criar novo investment
                new_investment = Investment(
                    id_usuario=id_usuario,
                    id_account=account.id,
                    nome=account.name or "Investimento",
                    tipo=tipo,
                    banco=banco_nome,
                    valor_inicial=valor_atual,
                    valor_atual=valor_atual,
                    fonte="PLUGGY",
                    ativo=True
                )
                db.add(new_investment)
                db.flush()  # Para obter o ID
                
                logger.info(f"✅ Investment criado: {account.name} ({tipo}) - R$ {float(valor_atual):.2f}")
                
                # Criar snapshot inicial
                snapshot = InvestmentSnapshot(
                    id_investment=new_investment.id,
                    valor=valor_atual,
                    rentabilidade_periodo=Decimal(0),
                    rentabilidade_percentual=Decimal(0),
                    data_snapshot=date.today()
                )
                db.add(snapshot)
        
        db.commit()
        logger.info(f"💾 Investimentos sincronizados com sucesso para item {pluggy_item_id}")
        
    except Exception as e:
        logger.error(f"❌ Erro ao sincronizar investimentos: {e}", exc_info=True)
        db.rollback()


def _guess_investment_type(nome: str, subtype: Optional[str]) -> str:
    """
    Tenta adivinhar o tipo de investimento baseado no nome e subtype.
    
    Returns:
        Um dos tipos: CDB, LCI, LCA, POUPANCA, TESOURO, ACAO, FUNDO, COFRINHO, OUTRO
    """
    nome_lower = (nome or "").lower()
    subtype_lower = (subtype or "").lower()
    
    combinado = f"{nome_lower} {subtype_lower}"
    
    # Mapear palavras-chave para tipos
    if any(word in combinado for word in ["cdb", "certificado de deposito"]):
        return "CDB"
    elif any(word in combinado for word in ["lci", "credito imobiliario"]):
        return "LCI"
    elif any(word in combinado for word in ["lca", "agronegocio"]):
        return "LCA"
    elif any(word in combinado for word in ["poupanca", "poupança", "savings"]):
        return "POUPANCA"
    elif any(word in combinado for word in ["tesouro", "selic", "ipca", "prefixado"]):
        return "TESOURO"
    elif any(word in combinado for word in ["acao", "ação", "stock", "bolsa"]):
        return "ACAO"
    elif any(word in combinado for word in ["fundo", "fund"]):
        return "FUNDO"
    elif any(word in combinado for word in ["cofrinho", "cofre", "caixinha", "piggy"]):
        return "COFRINHO"
    else:
        return "OUTRO"


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
        
        # 🔍 LOG DETALHADO: Ver tipos de contas retornadas
        logger.info(f"📊 Total de {len(accounts)} conta(s) retornada(s) pela API Pluggy")
        import json
        for acc in accounts:
            logger.info(f"   💳 Conta: {acc.get('name')} | Tipo: {acc.get('type')} | Subtipo: {acc.get('subtype')}")
            # Log do JSON completo da conta para debug (ajuda a achar Cofrinhos escondidos)
            logger.info(f"   🔍 JSON Conta: {json.dumps(acc, indent=2, default=str)}")
        
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
        
        # Sincronizar investimentos (criar/atualizar registros de Investment)
        try:
            _sync_investments_from_accounts(pluggy_item.id, db, accounts)
        except Exception as e:
            logger.error(f"⚠️  Erro ao sincronizar investimentos: {e}", exc_info=True)
        
        # 📈 BUSCAR INVESTIMENTOS via endpoint /investments da Pluggy
        try:
            save_pluggy_investments_to_db(item_id, pluggy_item.id, db)
        except Exception as e:
            logger.error(f"⚠️  Erro ao buscar investimentos do endpoint /investments: {e}", exc_info=True)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao salvar PluggyAccounts: {e}", exc_info=True)
        return False
    finally:
        db.close()


def save_pluggy_investments_to_db(item_id: str, pluggy_item_id: int, db) -> bool:
    """
    Busca investimentos do endpoint /investments da Pluggy e salva no banco.
    
    Args:
        item_id: ID do item na Pluggy (string UUID)
        pluggy_item_id: ID local do PluggyItem no banco
        db: Sessão do banco de dados (já aberta)
    
    Returns:
        True se salvou com sucesso, False caso contrário
    """
    try:
        from models import PluggyItem, Investment, InvestmentSnapshot, Usuario
        from datetime import date
        from decimal import Decimal
        
        logger.info("=" * 80)
        logger.info("🚀 INICIANDO BUSCA DE INVESTIMENTOS VIA ENDPOINT /investments")
        logger.info(f"📋 Item ID: {item_id}")
        logger.info(f"📋 Pluggy Item ID: {pluggy_item_id}")
        logger.info("=" * 80)
        
        logger.info(f"📈 Buscando investimentos via /investments para item {item_id}...")
        
        # Buscar investimentos na API Pluggy
        logger.info(f"🔄 Fazendo requisição GET /investments?itemId={item_id}")
        try:
            investments_data = pluggy_request("GET", f"/investments", params={"itemId": item_id})
            import json
            logger.info(f"✅ Response da API Pluggy /investments: {json.dumps(investments_data, indent=2, default=str)}")
        except Exception as api_error:
            logger.warning(f"⚠️  Endpoint /investments não retornou dados para item {item_id}: {api_error}")
            return True  # Não é erro crítico - alguns bancos não têm investimentos
        
        investments = investments_data.get("results", [])
        
        if not investments:
            logger.warning(f"⚠️  Nenhum investimento encontrado via /investments para item {item_id}")
            logger.warning(f"📊 Response completo: {investments_data}")
            return True
        
        logger.info(f"💰 {len(investments)} investimento(s) encontrado(s) via API Pluggy!")
        logger.info(f"📋 Primeiro investimento: {investments[0] if investments else 'N/A'}")
        
        # Buscar item para pegar id_usuario e banco
        pluggy_item = db.query(PluggyItem).filter(PluggyItem.id == pluggy_item_id).first()
        if not pluggy_item:
            logger.error(f"❌ PluggyItem {pluggy_item_id} não encontrado")
            return False
        
        id_usuario = pluggy_item.id_usuario
        banco_nome = pluggy_item.connector_name
        
        saved_count = 0
        for inv_data in investments:
            try:
                # Verificar se investimento já existe (por código único)
                codigo = inv_data.get("code") or inv_data.get("name") or inv_data.get("id")
                
                existing_inv = db.query(Investment).filter(
                    Investment.id_usuario == id_usuario,
                    Investment.banco == banco_nome,
                    Investment.codigo == codigo
                ).first()
                
                # Extrair dados
                tipo = inv_data.get("type", "Desconhecido")
                nome = inv_data.get("name", codigo)
                quantidade = Decimal(str(inv_data.get("quantity", 0)))
                valor_atual = Decimal(str(inv_data.get("balance", 0)))
                valor_investido = Decimal(str(inv_data.get("investedAmount", valor_atual)))
                
                if existing_inv:
                    # Atualizar investimento existente
                    existing_inv.quantidade = quantidade
                    existing_inv.valor_atual = valor_atual
                    existing_inv.valor_investido = valor_investido
                    existing_inv.tipo = tipo
                    
                    # Criar snapshot
                    snapshot = InvestmentSnapshot(
                        id_investimento=existing_inv.id,
                        data=date.today(),
                        valor=valor_atual,
                        quantidade=quantidade
                    )
                    db.add(snapshot)
                    
                    logger.info(f"🔄 Investimento atualizado: {nome} = R$ {valor_atual}")
                else:
                    # Criar novo investimento
                    new_inv = Investment(
                        id_usuario=id_usuario,
                        tipo=tipo,
                        banco=banco_nome,
                        nome=nome,
                        codigo=codigo,
                        quantidade=quantidade,
                        valor_investido=valor_investido,
                        valor_atual=valor_atual,
                        data_aplicacao=date.today()
                    )
                    db.add(new_inv)
                    db.flush()  # Para obter o ID
                    
                    # Criar snapshot inicial
                    snapshot = InvestmentSnapshot(
                        id_investimento=new_inv.id,
                        data=date.today(),
                        valor=valor_atual,
                        quantidade=quantidade
                    )
                    db.add(snapshot)
                    
                    saved_count += 1
                    logger.info(f"✅ Novo investimento: {nome} ({tipo}) = R$ {valor_atual}")
                
            except Exception as inv_error:
                logger.error(f"❌ Erro ao processar investimento {inv_data.get('id')}: {inv_error}")
                continue
        
        db.commit()
        logger.info(f"💾 {saved_count} investimento(s) novo(s) salvo(s) via API Pluggy")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao salvar investimentos da API Pluggy: {e}", exc_info=True)
        return False


def sync_transactions_for_account(account_id: int, pluggy_account_id: str, days: int = 30) -> Dict:
    """
    Sincroniza transações de uma conta específica.
    
    Args:
        account_id: ID local da PluggyAccount
        pluggy_account_id: ID da account na Pluggy
        days: Quantidade de dias para buscar transações (padrão 30)
    
    Returns:
        Dict com estatísticas: {new: X, updated: Y, total: Z}
    """
    try:
        from database.database import get_db
        from models import PluggyAccount, PluggyTransaction
        from datetime import datetime, timedelta
        import json
        
        db = next(get_db())
        
        # Buscar informações da conta primeiro
        account = db.query(PluggyAccount).filter(PluggyAccount.id == account_id).first()
        if account:
            logger.info(f"🔍 Sincronizando conta: {account.name} (tipo: {account.type}, subtype: {account.subtype})")
        
        # Calcular data inicial
        date_from = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        date_to = datetime.now().strftime("%Y-%m-%d")
        
        # Buscar transações na API Pluggy com PAGINAÇÃO COMPLETA
        logger.info(f"🔄 Buscando transações da account {pluggy_account_id} (de {date_from} até {date_to})...")
        
        all_transactions = []
        page = 1
        total_pages = 1
        
        # Loop de paginação - buscar TODAS as páginas
        while page <= total_pages:
            try:
                logger.info(f"📄 Buscando página {page} de transações...")
                
                transactions_data = pluggy_request(
                    "GET", 
                    "/transactions", 
                    params={
                        "accountId": pluggy_account_id,
                        "from": date_from,
                        "to": date_to,
                        "page": page
                    }
                )
                
                # Log da resposta na primeira página (RESUMIDO para evitar spam)
                if page == 1:
                    logger.info(f"📡 Response da API Pluggy (página {page}): {len(transactions_data.get('results', []))} itens")
                
                page_transactions = transactions_data.get("results", [])
                total_pages = transactions_data.get("totalPages", 1)
                total_count = transactions_data.get("total", 0)
                
                logger.info(f"📊 Página {page}/{total_pages}: {len(page_transactions)} transações (total geral: {total_count})")
                
                all_transactions.extend(page_transactions)
                page += 1
                
            except Exception as api_error:
                logger.error(f"❌ Erro na API Pluggy ao buscar página {page}: {api_error}")
                # Se falhou na primeira página, retornar erro
                if page == 1:
                    return {"new": 0, "updated": 0, "total": 0, "error": str(api_error)}
                # Se falhou em páginas posteriores, continuar com o que já temos
                break
        
        logger.info(f"✅ Total de {len(all_transactions)} transações recuperadas de {page-1} página(s)")
        
        if len(all_transactions) > 0:
            # Log da primeira transação para debug (RESUMIDO)
            first_txn = all_transactions[0]
            logger.info(f"🔍 Exemplo de transação: ID={first_txn.get('id')}, Desc={first_txn.get('description')}, Amount={first_txn.get('amount')}")
        
        new_count = 0
        updated_count = 0
        
        for txn in all_transactions:
            # Verificar se transação já existe
            existing = db.query(PluggyTransaction).filter(
                PluggyTransaction.pluggy_transaction_id == txn["id"]
            ).first()
            
            # Extrair dados do estabelecimento/recebedor com mais detalhes
            merchant_name = None
            merchant_category = None
            
            # 1. Tentar do objeto merchant (comum em cartão de crédito)
            merchant_data = txn.get("merchant")
            if merchant_data:
                merchant_name = merchant_data.get("name") or merchant_data.get("businessName")
                merchant_category = merchant_data.get("category")
            
            # 2. Se não achou nome, tentar do paymentData (comum em PIX)
            if not merchant_name:
                payment_data = txn.get("paymentData")
                if payment_data:
                    # Tentar determinar a outra parte baseado no fluxo do dinheiro
                    amount = txn.get("amount", 0)
                    
                    # Se for saída (negativo), queremos saber quem recebeu
                    if amount < 0 and payment_data.get("receiver"):
                        merchant_name = payment_data.get("receiver").get("name")
                    
                    # Se for entrada (positivo), queremos saber quem pagou
                    elif amount > 0 and payment_data.get("payer"):
                        merchant_name = payment_data.get("payer").get("name")
                    
                    # Fallback: se ainda null, tenta receiver (padrão mais comum)
                    if not merchant_name and payment_data.get("receiver"):
                        merchant_name = payment_data.get("receiver").get("name")

            if existing:
                # Atualizar status se mudou
                changed = False
                if existing.status != txn.get("status"):
                    existing.status = txn.get("status")
                    changed = True
                
                # Atualizar merchant info se estiver faltando no banco e presente na API
                if not existing.merchant_name and merchant_name:
                    existing.merchant_name = merchant_name
                    changed = True
                
                if not existing.merchant_category and merchant_category:
                    existing.merchant_category = merchant_category
                    changed = True
                    
                if changed:
                    existing.updated_at = datetime.now()
                    updated_count += 1
            else:
                # Criar nova transação
                new_txn = PluggyTransaction(
                    id_account=account_id,
                    pluggy_transaction_id=txn["id"],
                    description=txn.get("description", "Sem descrição"),
                    amount=txn.get("amount", 0),
                    date=_parse_transaction_date(txn.get("date")),
                    category=txn.get("category"),
                    status=txn.get("status"),
                    type=txn.get("type"),
                    merchant_name=merchant_name,
                    merchant_category=merchant_category,
                    imported_to_lancamento=False
                )
                
                db.add(new_txn)
                new_count += 1
        
        db.commit()
        
        logger.info(f"✅ Sincronização concluída: {new_count} novas, {updated_count} atualizadas")
        
        return {
            "new": new_count,
            "updated": updated_count,
            "total": len(all_transactions)
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao sincronizar transações: {e}", exc_info=True)
        return {"new": 0, "updated": 0, "total": 0, "error": str(e)}
    finally:
        db.close()


def sync_all_transactions_for_user(user_id: int, days: int = 30) -> Dict:
    """
    Sincroniza transações de todas as contas do usuário.
    
    Args:
        user_id: Telegram ID do usuário
        days: Quantidade de dias para buscar transações
    
    Returns:
        Dict com estatísticas consolidadas
    """
    try:
        from database.database import get_db
        from models import Usuario, PluggyItem, PluggyAccount
        
        db = next(get_db())
        
        # Buscar usuário
        usuario = db.query(Usuario).filter(Usuario.telegram_id == user_id).first()
        if not usuario:
            logger.error(f"❌ Usuário {user_id} não encontrado")
            return {"error": "Usuário não encontrado"}
        
        # Buscar todos os items ativos do usuário
        items = db.query(PluggyItem).filter(
            PluggyItem.id_usuario == usuario.id,
            PluggyItem.status.in_(["UPDATED", "PARTIAL_SUCCESS"])
        ).all()
        
        if not items:
            logger.info(f"ℹ️  Usuário {user_id} não tem conexões ativas")
            return {"items": 0, "accounts": 0, "new": 0, "updated": 0}
        
        logger.info(f"🏦 {len(items)} item(s) encontrado(s) para sincronização")
        
        total_new = 0
        total_updated = 0
        total_accounts = 0
        
        for item in items:
            logger.info(f"🔍 Processando item: {item.connector_name} (status: {item.status})")
            
            # 🆕 ATUALIZAR CONTAS E INVESTIMENTOS DO BANCO
            try:
                logger.info(f"🔄 Atualizando lista de contas e investimentos para {item.connector_name}...")
                save_pluggy_accounts_to_db(item.pluggy_item_id)
                logger.info(f"✅ Contas e investimentos atualizados")
            except Exception as e:
                logger.warning(f"⚠️  Erro ao atualizar contas: {e}")
            
            # Buscar accounts deste item (agora atualizadas!)
            accounts = db.query(PluggyAccount).filter(
                PluggyAccount.id_item == item.id
            ).all()
            
            logger.info(f"📊 {len(accounts)} conta(s) encontrada(s) neste item")
            
            for account in accounts:
                total_accounts += 1
                
                logger.info(f"💳 Sincronizando conta: {account.name} (tipo: {account.type}, subtipo: {account.subtype})")
                
                # Sincronizar transações desta account
                stats = sync_transactions_for_account(
                    account.id, 
                    account.pluggy_account_id, 
                    days
                )
                
                if "error" in stats:
                    logger.error(f"❌ Erro ao sincronizar conta {account.name}: {stats['error']}")
                
                total_new += stats.get("new", 0)
                total_updated += stats.get("updated", 0)
        
        logger.info(
            f"✅ Sincronização completa para usuário {user_id}: "
            f"{total_new} novas transações em {total_accounts} contas"
        )
        
        return {
            "items": len(items),
            "accounts": total_accounts,
            "new": total_new,
            "updated": total_updated
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao sincronizar usuário {user_id}: {e}", exc_info=True)
        return {"error": str(e)}
    finally:
        db.close()


def fetch_bank_connection_stats(item_id: str) -> Dict:
    """
    🔍 Busca estatísticas da conexão bancária recém estabelecida.
    
    Retorna informações sobre:
    - Total de transações disponíveis
    - Saldo atual das contas
    - Investimentos encontrados
    - Faturas de cartão de crédito
    
    Args:
        item_id: ID do item Pluggy recém conectado
        
    Returns:
        Dict com estatísticas: {
            'total_transactions': int,
            'total_accounts': int,
            'total_investments': int,
            'accounts_summary': List[Dict],
            'investments_summary': List[Dict],
            'total_balance': Decimal
        }
    """
    try:
        from decimal import Decimal
        
        logger.info(f"🔍 Buscando estatísticas para item {item_id}")
        
        # 1️⃣ Buscar contas
        accounts_data = pluggy_request("GET", f"/accounts", params={"itemId": item_id})
        accounts = accounts_data.get("results", [])
        
        total_balance = Decimal(0)
        accounts_summary = []
        
        for account in accounts:
            balance = Decimal(account.get("balance", 0) or 0)
            total_balance += balance
            
            accounts_summary.append({
                'name': account.get('name', 'Conta'),
                'type': account.get('type', 'BANK'),
                'balance': balance,
                'credit_limit': Decimal(account.get('creditLimit', 0) or 0)
            })
        
        # 2️⃣ Buscar transações (conta quantas existem)
        total_transactions = 0
        for account in accounts:
            try:
                transactions_data = pluggy_request(
                    "GET", 
                    f"/transactions", 
                    params={"accountId": account["id"], "pageSize": 1}  # Só pra contar
                )
                total_transactions += transactions_data.get("total", 0)
            except Exception as e:
                logger.warning(f"⚠️  Erro ao contar transações da conta {account['id']}: {e}")
        
        # 3️⃣ Buscar investimentos
        investments_summary = []
        try:
            investments_data = pluggy_request("GET", f"/investments", params={"itemId": item_id})
            investments = investments_data.get("results", [])
            
            for inv in investments:
                investments_summary.append({
                    'name': inv.get('name', 'Investimento'),
                    'type': inv.get('type', 'Desconhecido'),
                    'amount': Decimal(inv.get('amount', 0) or 0)
                })
                
        except Exception as e:
            logger.warning(f"⚠️  Erro ao buscar investimentos: {e}")
        
        stats = {
            'total_transactions': total_transactions,
            'total_accounts': len(accounts),
            'total_investments': len(investments_summary),
            'accounts_summary': accounts_summary,
            'investments_summary': investments_summary,
            'total_balance': total_balance
        }
        
        logger.info(f"✅ Estatísticas: {total_transactions} transações, {len(accounts)} contas, {len(investments_summary)} investimentos")
        
        return stats
        
    except Exception as e:
        logger.error(f"❌ Erro ao buscar estatísticas: {e}", exc_info=True)
        return {
            'total_transactions': 0,
            'total_accounts': 0,
            'total_investments': 0,
            'accounts_summary': [],
            'investments_summary': [],
            'total_balance': Decimal(0),
            'error': str(e)
        }


def calcular_limite_disponivel(conta_id: int, db) -> Dict:
    """
    💳 Calcula o limite disponível de um cartão de crédito.
    
    Fórmula: Limite Disponível = Limite Total - Σ(Faturas do mês atual para frente)
    
    Args:
        conta_id: ID da conta (cartão de crédito)
        db: Sessão do banco de dados
        
    Returns:
        Dict com informações: {
            'limite_total': Decimal,
            'limite_disponivel': Decimal,
            'fatura_atual': Decimal,
            'faturas_futuras': Decimal,
            'total_comprometido': Decimal
        }
    """
    try:
        from models import Conta, Lancamento
        from decimal import Decimal
        from datetime import datetime, date
        from dateutil.relativedelta import relativedelta
        
        # Buscar conta
        conta = db.query(Conta).filter(Conta.id == conta_id).first()
        
        if not conta or conta.tipo != 'Cartão de Crédito':
            return {
                'error': 'Conta não encontrada ou não é um cartão de crédito',
                'limite_total': Decimal(0),
                'limite_disponivel': Decimal(0),
                'fatura_atual': Decimal(0),
                'faturas_futuras': Decimal(0),
                'total_comprometido': Decimal(0)
            }
        
        limite_total = Decimal(conta.limite_cartao or 0)
        
        if limite_total == 0:
            return {
                'limite_total': Decimal(0),
                'limite_disponivel': Decimal(0),
                'fatura_atual': Decimal(0),
                'faturas_futuras': Decimal(0),
                'total_comprometido': Decimal(0),
                'warning': 'Limite não configurado'
            }
        
        # Data atual
        hoje = date.today()
        
        # Buscar TODAS as transações de Saída (gastos) do mês atual para frente
        lancamentos_futuros = db.query(Lancamento).filter(
            Lancamento.id_conta == conta_id,
            Lancamento.tipo == 'Saída',
            Lancamento.data_transacao >= datetime(hoje.year, hoje.month, 1)
        ).all()
        
        # Calcular total comprometido
        total_comprometido = sum(Decimal(lanc.valor) for lanc in lancamentos_futuros)
        
        # Separar fatura atual vs futuras (baseado no dia de fechamento)
        dia_fechamento = conta.dia_fechamento or 1
        
        # Data de fechamento do mês atual
        if hoje.day <= dia_fechamento:
            # Ainda estamos no período da fatura atual
            data_fechamento_atual = date(hoje.year, hoje.month, dia_fechamento)
        else:
            # Já passou o fechamento, estamos na próxima fatura
            proximo_mes = hoje + relativedelta(months=1)
            data_fechamento_atual = date(proximo_mes.year, proximo_mes.month, dia_fechamento)
        
        fatura_atual = Decimal(0)
        faturas_futuras = Decimal(0)
        
        for lanc in lancamentos_futuros:
            if lanc.data_transacao.date() <= data_fechamento_atual:
                fatura_atual += Decimal(lanc.valor)
            else:
                faturas_futuras += Decimal(lanc.valor)
        
        # Calcular limite disponível
        limite_disponivel = limite_total - total_comprometido
        
        return {
            'limite_total': limite_total,
            'limite_disponivel': max(limite_disponivel, Decimal(0)),  # Não pode ser negativo
            'fatura_atual': fatura_atual,
            'faturas_futuras': faturas_futuras,
            'total_comprometido': total_comprometido,
            'percentual_usado': (total_comprometido / limite_total * 100) if limite_total > 0 else Decimal(0)
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao calcular limite disponível: {e}", exc_info=True)
        return {
            'error': str(e),
            'limite_total': Decimal(0),
            'limite_disponivel': Decimal(0),
            'fatura_atual': Decimal(0),
            'faturas_futuras': Decimal(0),
            'total_comprometido': Decimal(0)
        }


class OpenFinanceOAuthHandler:
    """Handler para Open Finance com OAuth"""
    
    def __init__(self):
        self.active_connections: Dict[int, Dict] = {}  # user_id -> connection_data
    
    # ==================== /conectar_banco ====================
    
    async def conectar_banco_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Inicia processo de conexão Open Finance"""
        user_id = update.effective_user.id
        
        logger.info(f"👤 Usuário {user_id} iniciando conexão Open Finance")
        
        # 🔐 VERIFICAR WHITELIST
        from config import PLUGGY_WHITELIST_IDS
        if PLUGGY_WHITELIST_IDS and user_id not in PLUGGY_WHITELIST_IDS:
            logger.warning(f"🚫 Usuário {user_id} NÃO autorizado a usar Open Finance")
            await update.message.reply_text(
                "🔒 *Open Finance Restrito*\n\n"
                "Esta funcionalidade está temporariamente restrita durante o período de licença acadêmica.\n\n"
                "✅ Você ainda pode usar:\n"
                "• 📝 /adicionar - Lançamentos manuais\n"
                "• 📊 /resumo - Visualizar relatórios\n"
                "• 🎯 /metas - Gerenciar metas\n"
                "• 🤖 /gerente - Assistente financeiro IA\n"
                "• 💰 /investimentos - Cadastro manual\n\n"
                "💡 _Todas as outras funcionalidades do bot continuam disponíveis!_",
                parse_mode="Markdown"
            )
            return ConversationHandler.END
        
        # ⚠️ PROTEÇÃO: Verificar se já há conexão pendente
        now = datetime.now()
        if user_id in _pending_connections:
            pending = _pending_connections[user_id]
            elapsed = (now - pending["timestamp"]).total_seconds()
            
            # Se passou menos de 5 minutos, bloquear nova tentativa
            if elapsed < 300:  # 5 minutos
                await update.message.reply_text(
                    f"⏳ *Você já tem uma conexão em andamento!*\n\n"
                    f"🏦 Banco: {pending['connector_name']}\n"
                    f"⏱ Iniciada há {int(elapsed/60)} minuto(s)\n\n"
                    f"⚠️ Aguarde 5 minutos ou complete a conexão anterior antes de iniciar uma nova.\n\n"
                    f"💡 _Use /minhas_contas para ver suas conexões ativas._",
                    parse_mode="Markdown"
                )
                return ConversationHandler.END
            else:
                # Se passou mais de 5 minutos, limpar automaticamente
                logger.warning(f"🧹 Limpando conexão pendente expirada para usuário {user_id}")
                del _pending_connections[user_id]
        
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
            
            # Cores dos bancos (bolinhas coloridas)
            bank_colors = {
                "Nubank": "🟣",          # Roxo
                "Inter": "🟠",           # Laranja
                "Bradesco": "🔴",        # Vermelho
                "Itaú": "🔵",            # Azul
                "Itau": "🔵",            # Azul
                "Santander": "🔴",       # Vermelho
                "Mercado Pago": "🔵",    # Azul claro
                "XP": "⚫",              # Preto
                "Banco do Brasil": "🟡", # Amarelo
                "Caixa": "🔵",           # Azul
            }
            
            # Criar teclado inline
            keyboard = []
            for conn in display_connectors:
                # Buscar cor do banco
                emoji = "⚪"  # Branco padrão
                for bank_name, color in bank_colors.items():
                    if bank_name.lower() in conn['name'].lower():
                        emoji = color
                        break
                
                keyboard.append([
                    InlineKeyboardButton(
                        f"{emoji} {conn['name']}", 
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
            user_id = update.effective_user.id
            # ❌ LIMPAR conexão pendente (cancelada)
            if user_id in _pending_connections:
                del _pending_connections[user_id]
                logger.info(f"🧹 Conexão pendente removida para usuário {user_id} (cancelada)")
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
        
        # Identificar se é OAuth para mostrar mensagem diferente
        is_oauth = connector.get("oauth", False)
        
        if is_oauth:
            await query.edit_message_text(
                f"🏦 *{connector['name']}*\n\n"
                f"🔐 Este banco usa *Open Finance* (OAuth)\n"
                f"📝 Digite seu CPF para iniciar:\n\n"
                f"_Após informar o CPF, você será redirecionado para o site oficial do banco._",
                parse_mode="Markdown"
            )
        else:
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
        
        # Deletar mensagem com CPF (segurança) e confirmar com versão mascarada
        try:
            await update.message.delete()
        except:
            pass
        
        # Enviar confirmação com CPF mascarado
        cpf_masked = f"{cpf[:3]}.***.***-{cpf[-2:]}" if len(cpf) == 11 else "***"
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"✅ CPF recebido: `{cpf_masked}`\n🔄 Processando conexão...",
            parse_mode="Markdown"
        )
        
        status_msg = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"🔄 Criando conexão com *{connector['name']}*...",
            parse_mode="Markdown"
        )
        
        try:
            # Log do connector completo para debug
            import json
            logger.info(f"🔍 Connector selecionado: {json.dumps(connector, indent=2, default=str)}")
            
            # Criar item com CPF
            # Para OAuth: API retornará link de autenticação
            # Para legado: API tentará autenticar direto
            item_data = {
                "connectorId": connector["id"],
                "parameters": {"cpf": cpf}
            }
            
            is_oauth = connector.get("oauth", False)
            logger.info(f"🔐 Criando item {'OAuth' if is_oauth else 'legado'} (oauth={is_oauth}) com CPF para {connector['name']}")
            logger.info(f"📦 Payload enviado: {json.dumps(item_data, indent=2)}")
            
            item = pluggy_request("POST", "/items", data=item_data)
            item_id = item["id"]
            
            logger.info(f"✅ Item criado: {item_id} para usuário {user_id}")
            logger.info(f"📋 Response inicial: status={item.get('status')}, connector={connector.get('name')}, connectorId={connector.get('id')}")
            
            # Log completo do item para debug
            import json
            logger.info(f"🔍 Item completo: {json.dumps(item, indent=2, default=str)}")
            
            # Salvar item no contexto
            context.user_data["of_item_id"] = item_id
            context.user_data["of_item_status"] = item.get("status")
            
            # Salvar connector data para persistência futura
            self.active_connections[user_id] = {
                "item_id": item_id,
                "connector": connector,
                "created_at": datetime.now()
            }
            
            # ⚠️ PROTEÇÃO: Registrar conexão pendente
            _pending_connections[user_id] = {
                "item_id": item_id,
                "timestamp": datetime.now(),
                "connector_name": connector['name']
            }
            logger.info(f"🔒 Conexão pendente registrada para usuário {user_id}")
            
            # Aguardar alguns segundos para API processar
            await asyncio.sleep(3)
            
            # Consultar item novamente para pegar URL OAuth
            item_updated = pluggy_request("GET", f"/items/{item_id}")
            
            logger.info(f"📋 Item atualizado: status={item_updated.get('status')}")
            logger.info(f"🔍 Item atualizado completo: {json.dumps(item_updated, indent=2, default=str)}")
            
            # Procurar URL OAuth
            oauth_url = None
            parameter = item_updated.get("parameter", {})
            
            if parameter and parameter.get("type") == "oauth" and parameter.get("data"):
                oauth_url = parameter["data"]
                logger.info(f"🔗 OAuth URL encontrado em parameter.data: {oauth_url}")
            
            if not oauth_url:
                # Tentar em userAction
                user_action = item_updated.get("userAction")
                if user_action and user_action.get("url"):
                    oauth_url = user_action["url"]
                    logger.info(f"🔗 OAuth URL encontrado em userAction.url: {oauth_url}")
            
            if not oauth_url:
                logger.warning(f"⚠️  OAuth URL não encontrado. parameter={parameter}, userAction={item_updated.get('userAction')}")
            
            if oauth_url:
                # Criar botão inline com URL
                keyboard = [
                    [InlineKeyboardButton("🔐 Autorizar no Banco", url=oauth_url)],
                    [InlineKeyboardButton("✅ Já Autorizei", callback_data=f"of_authorized_{item_id}")],
                    [InlineKeyboardButton("❌ Cancelar", callback_data="of_cancel_auth")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                # Mensagem principal
                msg_text = (
                    f"🔐 *Autorização Necessária*\n\n"
                    f"🏦 Banco: *{connector['name']}*\n"
                    f"🆔 Conexão: `{item_id}`\n\n"
                    f"👉 Clique no botão abaixo para autorizar o acesso:\n\n"
                    f"⚠️ Você será redirecionado para o site oficial do banco.\n"
                    f"✅ Após autorizar, clique em *'Já Autorizei'*."
                )
                
                # Adicionar link bruto para casos de erro (ex: Bradesco no mobile)
                # Isso ajuda quando o deep link falha e abre a loja de apps
                msg_text += f"\n\n💡 *Problemas?* Copie e cole no navegador:\n`{oauth_url}`"

                await status_msg.edit_text(
                    msg_text,
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )
                
                # Iniciar polling em background
                asyncio.create_task(
                    self._poll_item_status(user_id, item_id, connector["name"], context, connector)
                )
                
                return WAITING_AUTH
                
            else:
                # Sem OAuth URL - verificar se precisa de autorização
                status = item_updated.get("status")
                
                # Se está OUTDATED ou WAITING_USER_INPUT, precisa autorizar no banco
                if status in ("OUTDATED", "WAITING_USER_INPUT", "LOGIN_ERROR"):
                    # Tentar obter URL de autenticação via userAction
                    user_action = item_updated.get("userAction")
                    auth_url = None
                    
                    if user_action:
                        auth_url = user_action.get("url") or user_action.get("instructions")
                    
                    # Se não tem URL, gerar instruções genéricas
                    if not auth_url:
                        await status_msg.edit_text(
                            f"🔐 *Autorização Pendente*\n\n"
                            f"🏦 Banco: *{connector['name']}*\n"
                            f"🆔 Conexão: `{item_id}`\n\n"
                            f"⚠️ *Ação Necessária:*\n"
                            f"1. Acesse o app/site do {connector['name']}\n"
                            f"2. Vá em Configurações → Open Finance\n"
                            f"3. Autorize o acesso do Maestro Financeiro\n\n"
                            f"Após autorizar, a sincronização começará automaticamente.\n\n"
                            f"Status atual: `{status}`",
                            parse_mode="Markdown"
                        )
                    else:
                        # Tem URL de autorização
                        keyboard = [
                            [InlineKeyboardButton("🔐 Autorizar no Banco", url=auth_url)],
                            [InlineKeyboardButton("✅ Já Autorizei", callback_data=f"of_authorized_{item_id}")],
                            [InlineKeyboardButton("❌ Cancelar", callback_data="of_cancel_auth")]
                        ]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        
                        await status_msg.edit_text(
                            f"🔐 *Autorização Pendente*\n\n"
                            f"🏦 Banco: *{connector['name']}*\n"
                            f"🆔 Conexão: `{item_id}`\n\n"
                            f"👉 Clique no botão para autorizar:\n\n"
                            f"Status: `{status}`",
                            reply_markup=reply_markup,
                            parse_mode="Markdown"
                        )
                    
                    # Polling em background - PASSAR connector como parâmetro
                    asyncio.create_task(
                        self._poll_item_status(user_id, item_id, connector["name"], context, connector)
                    )
                    
                    return WAITING_AUTH
                
                elif status in ("UPDATED", "PARTIAL_SUCCESS"):
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
                    
                    # Polling em background - PASSAR connector como parâmetro
                    asyncio.create_task(
                        self._poll_item_status(user_id, item_id, connector["name"], context, connector)
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
            user_id = update.effective_user.id
            # ❌ LIMPAR conexão pendente (autorização cancelada)
            if user_id in _pending_connections:
                del _pending_connections[user_id]
                logger.info(f"🧹 Conexão pendente removida para usuário {user_id} (auth cancelada)")
            await query.edit_message_text("❌ Autorização cancelada.")
            return ConversationHandler.END
        
        item_id = query.data.split("_")[-1]
        
        try:
            # Consultar status do item
            item = pluggy_request("GET", f"/items/{item_id}")
            status = item.get("status")
            
            if status in ("UPDATED", "PARTIAL_SUCCESS"):
                connector_name = item.get("connector", {}).get("name", "Banco")
                user_id = update.effective_user.id
                
                # ✅ LIMPAR conexão pendente (concluída com sucesso)
                if user_id in _pending_connections:
                    del _pending_connections[user_id]
                    logger.info(f"✅ Conexão pendente removida para usuário {user_id} (sucesso)")
                
                # 🔍 Buscar estatísticas da conexão
                stats = fetch_bank_connection_stats(item_id)
                
                # Montar mensagem com estatísticas
                total_trans = stats.get('total_transactions', 0)
                total_inv = stats.get('total_investments', 0)
                total_contas = stats.get('total_accounts', 0)
                
                mensagem = f"✅ *Banco conectado com sucesso!*\n\n"
                mensagem += f"🏦 *{connector_name}*\n\n"
                mensagem += f"📊 *Dados Encontrados:*\n"
                mensagem += f"💳 {total_contas} conta(s)\n"
                mensagem += f"📝 {total_trans} lançamento(s)\n"
                
                if total_inv > 0:
                    mensagem += f"📈 {total_inv} investimento(s)\n"
                
                mensagem += f"\n💡 Use /sincronizar para importar os dados\\!"
                
                # Botão para sincronizar
                keyboard = [
                    [InlineKeyboardButton("🔄 Sincronizar Agora", callback_data=f"of_sync_now_{item_id}")],
                    [InlineKeyboardButton("📋 Ver Contas", callback_data="of_view_accounts")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    mensagem,
                    parse_mode="MarkdownV2",
                    reply_markup=reply_markup
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
        
        # 🔐 VERIFICAR WHITELIST
        from config import PLUGGY_WHITELIST_IDS
        if PLUGGY_WHITELIST_IDS and user_id not in PLUGGY_WHITELIST_IDS:
            logger.warning(f"🚫 Usuário {user_id} NÃO autorizado a usar Open Finance")
            await update.message.reply_text(
                "🔒 *Open Finance Restrito*\n\n"
                "Esta funcionalidade está temporariamente restrita durante o período de licença acadêmica.",
                parse_mode="Markdown"
            )
            return
        
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
            
            # ✨ LAYOUT CONSOLIDADO: Cartões e Contas
            message = "💳 *Cartões e Contas*\n\n"
            
            # Emojis dos bancos
            bank_colors = {
                "Nubank": "🟣",
                "Inter": "🟠", 
                "Bradesco": "🔴",
                "Itaú": "🟧",
                "Itau": "��",
                "Santander": "🔺",
                "Banco do Brasil": "🟨",
                "Caixa": "🟦",
                "Mercado Pago": "🔵",
                "XP": "⚫",
            }
            
            for item in items:
                # Buscar cor do banco
                bank_emoji = "⚪"
                for bank_name, color in bank_colors.items():
                    if bank_name.lower() in item.connector_name.lower():
                        bank_emoji = color
                        break
                
                # Nome do banco escapado
                safe_bank = escape_markdown_v2(item.connector_name)
                
                message += f"{bank_emoji} *{safe_bank}*\n"
                
                # Buscar todas as accounts deste banco (cartão + conta)
                accounts = db.query(PluggyAccount).filter(
                    PluggyAccount.id_item == item.id
                ).all()
                
                if not accounts:
                    message += "ℹ️ _Nenhuma conta encontrada_\n"
                    message += "━━━━━━━━━━━━━━━━━━━━━━\n"
                    continue
                
                # Separar por tipo
                bank_accounts = [a for a in accounts if a.type == "BANK"]
                credit_cards = [a for a in accounts if a.type == "CREDIT"]
                investments = [a for a in accounts if a.type == "INVESTMENT"]
                
                # DEBUG: Logar tipos encontrados
                logger.info(f"🏦 {item.connector_name}: {len(bank_accounts)} BANK, {len(credit_cards)} CREDIT, {len(investments)} INVESTMENT")
                for acc in accounts:
                    logger.info(f"   📋 {acc.name}: tipo={acc.type}, balance={acc.balance}, credit_limit={acc.credit_limit}")
                
                # Saldo (contas bancárias)
                if bank_accounts:
                    total_balance = sum(float(a.balance) for a in bank_accounts if a.balance is not None)
                    balance_str = f"R$ {total_balance:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                    # Escapar caracteres especiais para MarkdownV2
                    balance_str = escape_markdown_v2(balance_str)
                    message += f"💰 Saldo: {balance_str}\n"
                
                
                # Cartões de crédito com limite disponível
                if credit_cards:
                    for card in credit_cards:
                        card_name = escape_markdown_v2(card.name or "Cartão")
                        message += f"💳 _{card_name}_\n"
                        
                        # Pluggy retorna:
                        # - balance: Valor UTILIZADO do limite (Fatura Atual)
                        # - credit_limit: Limite TOTAL do cartão
                        
                        # Valores padrão
                        limite_total = float(card.credit_limit) if card.credit_limit is not None else 0
                        valor_utilizado = float(card.balance) if card.balance is not None else 0
                        
                        # Calcular fatura atual e limite disponível
                        fatura_atual = valor_utilizado
                        limite_disponivel = max(0, limite_total - valor_utilizado)
                        
                        # Emoji baseado no percentual usado
                        percentual_usado = (fatura_atual / limite_total * 100) if limite_total > 0 else 0
                        if percentual_usado < 30:
                            emoji = "🟢"
                        elif percentual_usado < 70:
                            emoji = "🟡"
                        else:
                            emoji = "🔴"
                        
                        # Exibir apenas se há dados válidos
                        if limite_total > 0:
                            # Limite Total
                            limite_total_str = f"R$ {limite_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                            limite_total_str = escape_markdown_v2(limite_total_str)
                            message += f"   💰 Limite: {limite_total_str}\n"
                            
                            # Fatura Atual
                            fatura_str = f"R$ {fatura_atual:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                            fatura_str = escape_markdown_v2(fatura_str)
                            message += f"   {emoji} Fatura: {fatura_str} \\({percentual_usado:.0f}%\\)\n"
                            
                            # Disponível
                            limite_disp_str = f"R$ {limite_disponivel:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                            limite_disp_str = escape_markdown_v2(limite_disp_str)
                            message += f"   ✅ Disponível: {limite_disp_str}\n"
                        else:
                            message += f"   ⚠️ _Aguardando sincronização\\.\\.\\._\n"
                
                # Investimentos (se houver) - MELHORADO
                if investments:
                    total_inv = sum(float(i.balance) for i in investments if i.balance is not None)
                    if total_inv > 0:
                        inv_str = f"R$ {total_inv:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                        inv_str = escape_markdown_v2(inv_str)
                        message += f"📈 *Investimentos:* {inv_str}\n"
                        
                        # Mostrar quantos investimentos
                        qtd_inv = len(investments)
                        message += f"   _{qtd_inv} produto\\(s\\) de investimento_\n"
                
                message += "━━━━━━━━━━━━━━━━━━━━━━\n"
            
            # 💎 RESUMO TOTAL (opcional - se tiver investimentos)
            from models import Investment
            total_investimentos_db = db.query(Investment).filter(
                Investment.id_usuario == usuario.id,
                Investment.ativo == True
            ).all()
            
            if total_investimentos_db:
                valor_total_inv = sum(float(inv.valor_atual) for inv in total_investimentos_db)
                inv_total_str = f"R$ {valor_total_inv:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                inv_total_str = escape_markdown_v2(inv_total_str)
                message += f"\n💎 *Total Investido:* {inv_total_str}\n"
                message += f"_{len(total_investimentos_db)} investimento\\(s\\) ativo\\(s\\)_\n\n"
            
            # Botões de ação
            keyboard = [
                [InlineKeyboardButton("🔄 Sincronizar", callback_data="action_sync")],
                [InlineKeyboardButton("➕ Conectar Banco", callback_data="action_connect")],
            ]
            
            # Adicionar botão de investimentos se houver
            if total_investimentos_db:
                keyboard.insert(1, [InlineKeyboardButton("� Ver Investimentos", url="https://t.me/your_bot?start=investimentos")])
            
            keyboard.append([InlineKeyboardButton("�🗑️ Desconectar Banco", callback_data="action_disconnect")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            message += "\n_Use os botões abaixo:_"
            
            await update.message.reply_text(message, reply_markup=reply_markup, parse_mode="MarkdownV2")
            
        except Exception as e:
            logger.error(f"❌ Erro ao listar contas: {e}", exc_info=True)
            await update.message.reply_text(
                "❌ Erro ao buscar suas contas.\n"
                "Tente novamente em alguns instantes."
            )
        finally:
            db.close()
    
    # ==================== /sincronizar ====================
    
    async def sincronizar(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Sincroniza transações bancárias manualmente"""
        user_id = update.effective_user.id
        
        logger.info(f"👤 Usuário {user_id} solicitou sincronização manual")
        
        # 🔐 VERIFICAR WHITELIST
        from config import PLUGGY_WHITELIST_IDS
        if PLUGGY_WHITELIST_IDS and user_id not in PLUGGY_WHITELIST_IDS:
            logger.warning(f"🚫 Usuário {user_id} NÃO autorizado a usar Open Finance")
            await update.message.reply_text(
                "🔒 *Open Finance Restrito*\n\n"
                "Esta funcionalidade está temporariamente restrita durante o período de licença acadêmica.",
                parse_mode="Markdown"
            )
            return
        
        status_msg = await update.message.reply_text(
            "🔄 Sincronizando transações bancárias...\n"
            "Isso pode levar alguns segundos."
        )
        
        try:
            # Sincronizar transações
            stats = sync_all_transactions_for_user(user_id, days=30)
            
            if "error" in stats:
                await status_msg.edit_text(
                    f"❌ Erro na sincronização:\n{stats['error']}"
                )
                return
            
            if stats.get("accounts", 0) == 0:
                await status_msg.edit_text(
                    "ℹ️  Você não tem contas conectadas.\n\n"
                    "Use /conectar_banco para conectar um banco."
                )
                return
            
            # Montar mensagem de resultado
            new = stats.get("new", 0)
            accounts = stats.get("accounts", 0)
            
            if new == 0:
                message = (
                    "✅ *Sincronização concluída\\!*\n\n"
                    f"📊 {accounts} conta\\(s\\) verificada\\(s\\)\n"
                    f"ℹ️  Nenhuma transação nova encontrada\\.\n\n"
                    f"_Todas as suas transações já estão sincronizadas\\!_\n\n"
                    f"⚠️ *Nota:* Alguns bancos não disponibilizam transações detalhadas de cartão de crédito via Open Finance\\. "
                    f"O saldo e limite são atualizados\\, mas as compras individuais podem não aparecer\\."
                )
            else:
                message = (
                    f"✅ *Sincronização concluída\\!*\n\n"
                    f"📊 {accounts} conta\\(s\\) verificada\\(s\\)\n"
                    f"🆕 *{new} nova\\(s\\) transação\\(ões\\)* encontrada\\(s\\)\\!\n\n"
                    f"Use /importar\\_transacoes para importar\\."
                )
                
                # Notificar usuário sobre novas transações
                await self._notify_new_transactions(user_id, new, context)
            
            await status_msg.edit_text(message, parse_mode="MarkdownV2")
            
        except Exception as e:
            logger.error(f"❌ Erro na sincronização: {e}", exc_info=True)
            await status_msg.edit_text(
                "❌ Erro ao sincronizar transações.\n"
                "Tente novamente em alguns instantes."
            )
    
    # ==================== /importar_transacoes ====================
    
    async def importar_transacoes(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Lista transações não importadas para o usuário importar"""
        user_id = update.effective_user.id
        
        logger.info(f"👤 Usuário {user_id} acessando importação de transações")
        
        # 🔐 VERIFICAR WHITELIST
        from config import PLUGGY_WHITELIST_IDS
        if PLUGGY_WHITELIST_IDS and user_id not in PLUGGY_WHITELIST_IDS:
            logger.warning(f"🚫 Usuário {user_id} NÃO autorizado a usar Open Finance")
            await update.message.reply_text(
                "🔒 *Open Finance Restrito*\n\n"
                "Esta funcionalidade está temporariamente restrita durante o período de licença acadêmica.",
                parse_mode="Markdown"
            )
            return
        
        try:
            from database.database import get_db
            from models import Usuario, PluggyTransaction, PluggyAccount, PluggyItem
            from sqlalchemy import and_
            
            db = next(get_db())
            
            # Buscar usuário
            usuario = db.query(Usuario).filter(Usuario.telegram_id == user_id).first()
            if not usuario:
                await update.message.reply_text("❌ Usuário não encontrado.")
                return
            
            # Buscar transações não importadas do usuário
            # Join: PluggyTransaction -> PluggyAccount -> PluggyItem -> Usuario
            pending_txns = (
                db.query(PluggyTransaction)
                .join(PluggyAccount, PluggyTransaction.id_account == PluggyAccount.id)
                .join(PluggyItem, PluggyAccount.id_item == PluggyItem.id)
                .filter(
                    and_(
                        PluggyItem.id_usuario == usuario.id,
                        PluggyTransaction.imported_to_lancamento == False
                    )
                )
                .order_by(PluggyTransaction.date.desc())
                .all()  # ✅ Buscar TODAS as transações pendentes (removido limite)
            )
            
            if not pending_txns:
                await update.message.reply_text(
                    "✅ *Tudo em dia\\!*\n\n"
                    "Você não tem transações pendentes de importação\\.\n\n"
                    "Use /sincronizar para buscar novas transações\\.",
                    parse_mode="MarkdownV2"
                )
                return
            
            # Criar botões inline para cada transação
            message = f"💳 *Transações Pendentes* \\({len(pending_txns)}\\)\n\n"
            message += "Clique para importar:\n\n"
            
            keyboard = []
            for idx, txn in enumerate(pending_txns[:10], 1):  # Mostrar apenas 10 por vez
                # ✅ CORREÇÃO: Determinar cor baseado no tipo de conta
                account = db.query(PluggyAccount).filter(PluggyAccount.id == txn.id_account).first()
                is_credit_card = account and account.type == "CREDIT"
                
                # Para cartão: amount > 0 = GASTO (vermelho), amount < 0 = pagamento (verde)
                # Para conta normal: amount < 0 = GASTO (vermelho), amount > 0 = receita (verde)
                if is_credit_card:
                    emoji = "🔴" if float(txn.amount) > 0 else "🟢"  # Invertido para CC
                else:
                    emoji = "🔴" if float(txn.amount) < 0 else "🟢"  # Normal para contas
                
                # Formatar valor (sem pontos, pois vai em botão inline - não precisa escape)
                amount_str = f"R$ {abs(float(txn.amount)):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                
                # Truncar descrição
                desc = txn.description[:30] + "..." if len(txn.description) > 30 else txn.description
                desc_safe = desc.replace("_", " ").replace("*", " ").replace("[", " ")
                
                date_str = txn.date.strftime("%d/%m")
                
                button_text = f"{emoji} {date_str} - {desc_safe} - {amount_str}"
                keyboard.append([
                    InlineKeyboardButton(
                        button_text, 
                        callback_data=f"import_txn_{txn.id}"
                    )
                ])
            
            # Botões de ação
            keyboard.append([
                InlineKeyboardButton("✅ Importar Todas", callback_data="import_all"),
                InlineKeyboardButton("❌ Cancelar", callback_data="import_cancel")
            ])
            
            if len(pending_txns) > 10:
                message += f"\n\n_Mostrando 10 de {len(pending_txns)} transações\\._"
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                message, 
                reply_markup=reply_markup,
                parse_mode="MarkdownV2"
            )
            
        except Exception as e:
            logger.error(f"❌ Erro ao listar transações: {e}", exc_info=True)
            await update.message.reply_text(
                "❌ Erro ao buscar transações.\n"
                "Tente novamente em alguns instantes."
            )
        finally:
            db.close()
    
    async def _notify_new_transactions(self, user_id: int, count: int, context: ContextTypes.DEFAULT_TYPE):
        """Notifica usuário sobre novas transações (interno)"""
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    f"🔔 *Nova\\(s\\) transação\\(ões\\) detectada\\(s\\)\\!*\n\n"
                    f"Encontrei *{count} nova\\(s\\) transação\\(ões\\)* nas suas contas bancárias\\.\n\n"
                    f"Use /importar\\_transacoes para revisar e importar\\."
                ),
                parse_mode="MarkdownV2"
            )
        except Exception as e:
            logger.error(f"❌ Erro ao notificar usuário: {e}")
    
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
        connector: dict,  # NOVO: connector passado como parâmetro
        max_attempts: int = 60  # 60 tentativas x 5s = 5 minutos
    ):
        """Faz polling do status do item em background"""
        logger.info(f"🔄 Iniciando polling para item {item_id} (connector: {connector.get('name')})")
        
        oauth_url_sent = False  # Flag para evitar enviar OAuth URL múltiplas vezes
        attempt = 0
        last_execution_status = None
        
        while attempt < max_attempts:
            try:
                await asyncio.sleep(5)  # Aguardar 5 segundos entre tentativas
                attempt += 1
                
                item = pluggy_request("GET", f"/items/{item_id}")
                status = item.get("status")
                execution_status = item.get("executionStatus")
                
                logger.info(f"📊 Polling item {item_id}: tentativa {attempt}/{max_attempts}, status={status}, executionStatus={execution_status}")
                
                # Detectar mudança no executionStatus (indica progresso)
                if last_execution_status and execution_status != last_execution_status:
                    logger.info(f"🔄 ExecutionStatus mudou: {last_execution_status} → {execution_status}")
                last_execution_status = execution_status
                
                # Se está OUTDATED ou WAITING_USER_INPUT e ainda não enviamos OAuth URL
                if status in ("OUTDATED", "WAITING_USER_INPUT") and not oauth_url_sent:
                    # Tentar extrair OAuth URL do item
                    oauth_url = None
                    
                    # Verificar no campo parameter.data
                    if "parameter" in item and isinstance(item["parameter"], dict):
                        param_data = item["parameter"].get("data", {})
                        if isinstance(param_data, dict):
                            oauth_url = param_data.get("authorizationUrl") or param_data.get("url")
                    
                    # Verificar no campo userAction
                    if not oauth_url and "userAction" in item:
                        user_action = item["userAction"]
                        if isinstance(user_action, dict):
                            oauth_url = user_action.get("url") or user_action.get("authorizationUrl")
                    
                    # Se encontrou OAuth URL, enviar para o usuário
                    if oauth_url:
                        logger.info(f"🔗 OAuth URL encontrado no polling: {oauth_url}")
                        
                        keyboard = [
                            [InlineKeyboardButton("🔐 Autorizar no Banco", url=oauth_url)],
                            [InlineKeyboardButton("✅ Já Autorizei", callback_data=f"of_authorized_{item_id}")],
                            [InlineKeyboardButton("❌ Cancelar", callback_data="of_cancel_auth")]
                        ]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        
                        safe_bank_name = bank_name.replace("_", "\\_").replace("*", "\\*").replace("[", "\\[").replace("`", "\\`")
                        
                        # Escape URL for MarkdownV2 code block
                        # In MarkdownV2 code blocks, only ` and \ need escaping
                        safe_url = oauth_url.replace("\\", "\\\\").replace("`", "\\`")
                        
                        await context.bot.send_message(
                            chat_id=user_id,
                            text=f"🔐 *Autorização Necessária*\n\n"
                                 f"🏦 Banco: *{safe_bank_name}*\n"
                                 f"🆔 Conexão: `{item_id}`\n\n"
                                 f"👉 Clique no botão abaixo para autorizar o acesso:\n\n"
                                 f"⚠️ Você será redirecionado para o site oficial do banco\\.\n"
                                 f"✅ Após autorizar, clique em *'Já Autorizei'*\\.\n\n"
                                 f"💡 *Problemas?* Copie e cole no navegador:\n"
                                 f"`{safe_url}`",
                            reply_markup=reply_markup,
                            parse_mode="MarkdownV2"
                        )
                        
                        oauth_url_sent = True
                        logger.info(f"✅ OAuth URL enviado para usuário {user_id}")
                
                # Status de sucesso - verificar TANTO status quanto executionStatus
                if status in ("UPDATED", "PARTIAL_SUCCESS") or execution_status in ("SUCCESS", "PARTIAL_SUCCESS"):
                    # ✅ LIMPAR conexão pendente (sucesso)
                    if user_id in _pending_connections:
                        del _pending_connections[user_id]
                        logger.info(f"✅ Conexão pendente removida para usuário {user_id} (polling success)")
                    
                    # 💾 Salvar item e accounts no banco de dados
                    try:
                        # Connector passado como parâmetro - garantido disponível
                        save_success = save_pluggy_item_to_db(user_id, item, connector)
                        if save_success:
                            logger.info(f"💾 Dados do item {item_id} salvos no banco (connector={connector.get('name')})")
                        else:
                            logger.warning(f"⚠️  Falha ao salvar dados do item {item_id} no banco")
                    except Exception as save_error:
                        logger.error(f"❌ Erro ao salvar item no banco: {save_error}", exc_info=True)
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
                    logger.info(f"✅ Item {item_id} conectado com sucesso (status={status}, executionStatus={execution_status})")
                    break
                
                # Status de erro
                if status in ("LOGIN_ERROR", "INVALID_CREDENTIALS", "ERROR", "SUSPENDED"):
                    # ✅ LIMPAR conexão pendente (erro)
                    if user_id in _pending_connections:
                        del _pending_connections[user_id]
                        logger.info(f"❌ Conexão pendente removida para usuário {user_id} (erro)")
                    
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
                    logger.warning(f"❌ Item {item_id} falhou: {status} - {status_detail}")
                    break
                
            except Exception as e:
                logger.error(f"❌ Erro no polling do item {item_id} (tentativa {attempt}): {e}")
                # Continuar tentando mesmo com erros
        
        # Se saiu do loop por timeout (não por break)
        if attempt >= max_attempts:
            logger.warning(f"⏰ Timeout no polling do item {item_id} após {attempt} tentativas ({max_attempts*5}s)")
            
            # ✅ LIMPAR conexão pendente (timeout)
            if user_id in _pending_connections:
                del _pending_connections[user_id]
                logger.info(f"⏰ Conexão pendente removida para usuário {user_id} (timeout)")
            
            try:
                safe_bank_name = bank_name.replace("_", "\\_").replace("*", "\\*").replace("[", "\\[").replace("`", "\\`")
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"⏰ *Tempo esgotado*\n\n"
                         f"🏦 {safe_bank_name}\n"
                         f"⏳ A sincronização está demorando mais que 5 minutos\\.\n\n"
                         f"✅ A conexão pode ter sido concluída\\. Verifique com:\n"
                         f"• /minhas\\_contas \\- Ver contas conectadas\n"
                         f"• /sincronizar \\- Tentar sincronizar novamente\n\n"
                         f"❌ Se não funcionou, tente reconectar com /conectar\\_banco",
                    parse_mode="MarkdownV2"
                )
            except Exception as e:
                logger.error(f"❌ Erro ao enviar mensagem de timeout: {e}")
    
    # ==================== ACTION CALLBACKS (MINHAS_CONTAS) ====================
    
    async def handle_action_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Processa callbacks dos botões de ação do /minhas_contas"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == "action_sync":
            # Redirecionar para sincronização
            await query.message.reply_text("🔄 Iniciando sincronização...")
            # Simular comando /sincronizar
            await self.sincronizar(query, context)
            return
        
        elif data == "action_connect":
            await query.message.reply_text(
                "➕ Para conectar um novo banco, use:\n/conectar_banco"
            )
            return
        
        elif data == "action_disconnect":
            await query.message.reply_text(
                "🗑️ Para desconectar um banco, use:\n/desconectar_banco"
            )
            return
    
    # ==================== IMPORT CALLBACKS ====================
    
    async def handle_import_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Processa callbacks dos botões de importação"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        user_id = query.from_user.id
        
        if data == "import_cancel":
            await query.edit_message_text("❌ Importação cancelada.")
            return
        
        if data == "import_all":
            # Importar todas as transações pendentes
            await self._import_all_transactions(user_id, query)
            return
        
        if data.startswith("import_txn_"):
            # Importar transação específica
            txn_id = int(data.replace("import_txn_", ""))
            await self._import_single_transaction(user_id, txn_id, query, context)
            return
    
    async def _import_single_transaction(self, user_id: int, txn_id: int, query, context):
        """Importa uma transação específica"""
        try:
            from database.database import get_db
            from models import Usuario, PluggyTransaction, Lancamento, Categoria
            
            db = next(get_db())
            
            # Buscar transação
            txn = db.query(PluggyTransaction).filter(PluggyTransaction.id == txn_id).first()
            if not txn:
                await query.edit_message_text("❌ Transação não encontrada.")
                return
            
            # Buscar usuário
            usuario = db.query(Usuario).filter(Usuario.telegram_id == user_id).first()
            if not usuario:
                await query.edit_message_text("❌ Usuário não encontrado.")
                return
            
            # Sugerir categoria baseado no merchant ou descrição
            suggested_category = self._suggest_category(txn.description, txn.merchant_name, db)
            
            # Determinar tipo (receita ou despesa)
            # IMPORTANTE: Para cartões de crédito, a lógica é INVERTIDA!
            # - Gastos no cartão: amount > 0 (mas é DESPESA)
            # - Pagamento de fatura: amount < 0 (mas é CRÉDITO/redução da dívida)
            from models import PluggyAccount
            account = db.query(PluggyAccount).filter(PluggyAccount.id == txn.id_account).first()
            
            is_credit_card = account and account.type == "CREDIT"
            
            # 🔍 LOG DETALHADO PARA DEBUG
            logger.info(f"🔍 Analisando transação {txn.id}:")
            logger.info(f"   📝 Descrição: {txn.description}")
            logger.info(f"   💰 Amount: {float(txn.amount)}")
            logger.info(f"   🏷️ Type API: {txn.type}")  # CREDIT ou DEBIT vindo da Pluggy
            logger.info(f"   💳 Tipo conta: {account.type if account else 'UNKNOWN'}")
            logger.info(f"   🏦 Nome conta: {account.name if account else 'UNKNOWN'}")
            logger.info(f"   ❓ É cartão crédito? {is_credit_card}")
            
            if is_credit_card:
                # ⚠️ LÓGICA CORRIGIDA: Para cartão de crédito a API Pluggy INVERTE os types!
                # - Compras (gastos): vêm como type="CREDIT" + amount positivo (mas é DESPESA)
                # - Pagamentos fatura: vêm como type="CREDIT" + amount negativo (é pagamento)
                # 
                # Nossa lógica: amount > 0 no CC = DESPESA, amount < 0 = pagamento (ignorar)
                if float(txn.amount) < 0:
                    # Pagamento de fatura - não importar
                    logger.info(f"⏭️ Transação {txn.id} é pagamento de fatura - pulando importação")
                    await query.edit_message_text(
                        "ℹ️ *Pagamento de fatura detectado*\n\n"
                        "Esta transação é um pagamento de fatura do cartão\\.\n"
                        "Não será importada para evitar duplicação\\.",
                        parse_mode="MarkdownV2"
                    )
                    return
                else:
                    # ✅ CORREÇÃO: IGNORAMOS o "type" da API para cartões
                    # Amount positivo em CC = GASTO (DESPESA), independente do "type" ser "CREDIT"
                    tipo = "Despesa"  # Gasto no cartão - SEMPRE DESPESA
                    logger.info(f"✅ Cartão de crédito: categorizando como DESPESA (amount positivo, ignorando type='{txn.type}')")
            else:
                # Para conta corrente/poupança: lógica normal
                tipo = "Receita" if float(txn.amount) > 0 else "Despesa"
                logger.info(f"✅ Conta normal: amount={'positivo' if float(txn.amount) > 0 else 'negativo'} → {tipo.upper()}")
            
            # Criar lançamento
            # CORREÇÃO: usar nome do banco/conta em vez de string genérica
            nome_banco = account.name if account else "Sem conta"
            lancamento = Lancamento(
                descricao=txn.description,
                valor=abs(float(txn.amount)),
                tipo=tipo,
                data_transacao=datetime.combine(txn.date, datetime.min.time()),
                forma_pagamento=nome_banco,  # ✅ Nome real: "Nubank", "Itaú", etc.
                id_usuario=usuario.id,
                id_categoria=suggested_category.id if suggested_category else None
            )
            
            db.add(lancamento)
            
            # Marcar transação como importada
            txn.imported_to_lancamento = True
            txn.id_lancamento = lancamento.id
            
            db.commit()
            
            # Formatar mensagem
            amount_str = f"R$ {abs(float(txn.amount)):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            # Escapar caracteres especiais para MarkdownV2
            amount_str = escape_markdown_v2(amount_str)
            cat_name = suggested_category.nome if suggested_category else "Sem categoria"
            cat_name_safe = escape_markdown_v2(cat_name)
            desc_safe = escape_markdown_v2(txn.description)
            
            await query.edit_message_text(
                f"✅ *Transação importada\\!*\n\n"
                f"📝 {desc_safe}\n"
                f"💰 {amount_str}\n"
                f"📂 Categoria: {cat_name_safe}\n"
                f"📅 Data: {txn.date.strftime('%d/%m/%Y')}\n\n"
                f"Use /importar\\_transacoes para continuar\\.",
                parse_mode="MarkdownV2"
            )
            
            logger.info(f"✅ Transação {txn_id} importada para usuário {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Erro ao importar transação: {e}", exc_info=True)
            await query.edit_message_text("❌ Erro ao importar transação.")
        finally:
            db.close()
    
    async def _import_all_transactions(self, user_id: int, query):
        """Importa todas as transações pendentes"""
        try:
            from database.database import get_db
            from models import Usuario, PluggyTransaction, Lancamento, PluggyAccount, PluggyItem
            from sqlalchemy import and_
            
            db = next(get_db())
            
            # Buscar usuário
            usuario = db.query(Usuario).filter(Usuario.telegram_id == user_id).first()
            if not usuario:
                await query.edit_message_text("❌ Usuário não encontrado.")
                return
            
            # Buscar todas transações pendentes
            pending_txns = (
                db.query(PluggyTransaction)
                .join(PluggyAccount, PluggyTransaction.id_account == PluggyAccount.id)
                .join(PluggyItem, PluggyAccount.id_item == PluggyItem.id)
                .filter(
                    and_(
                        PluggyItem.id_usuario == usuario.id,
                        PluggyTransaction.imported_to_lancamento == False
                    )
                )
                .all()
            )
            
            if not pending_txns:
                await query.edit_message_text("✅ Nenhuma transação pendente.")
                return
            
            imported_count = 0
            skipped_count = 0
            
            for txn in pending_txns:
                try:
                    # Buscar conta para verificar tipo
                    account = db.query(PluggyAccount).filter(PluggyAccount.id == txn.id_account).first()
                    is_credit_card = account and account.type == "CREDIT"
                    
                    # 🔍 LOG DETALHADO PARA DEBUG
                    logger.info(f"🔍 [MASSA] Transação {txn.id}: {txn.description} | Amount: {float(txn.amount)} | Type API: {txn.type} | Tipo conta: {account.type if account else 'UNKNOWN'} | É CC? {is_credit_card}")
                    
                    # Para cartão de crédito, pular pagamentos de fatura
                    if is_credit_card and float(txn.amount) < 0:
                        logger.info(f"⏭️ Transação {txn.id} é pagamento de fatura - pulando")
                        txn.imported_to_lancamento = True  # Marcar como "importada" para não aparecer de novo
                        skipped_count += 1
                        continue
                    
                    # Sugerir categoria
                    suggested_category = self._suggest_category(txn.description, txn.merchant_name, db)
                    
                    # ⚠️ CORREÇÃO: Determinar tipo ignorando "type" da API para cartões
                    # A Pluggy inverte: compras em CC vêm como type="CREDIT" mas são DESPESAS
                    if is_credit_card:
                        tipo = "Despesa"  # Gastos no cartão são SEMPRE despesa (ignorando type da API)
                        logger.info(f"✅ [MASSA] Cartão de crédito: {txn.id} → DESPESA (ignorando type='{txn.type}')")
                    else:
                        tipo = "Receita" if float(txn.amount) > 0 else "Despesa"
                        logger.info(f"✅ [MASSA] Conta normal: {txn.id} → {tipo.upper()} (amount={'positivo' if float(txn.amount) > 0 else 'negativo'})")
                    
                    # Criar lançamento
                    # CORREÇÃO: usar nome do banco/conta em vez de string genérica
                    nome_banco = account.name if account else "Sem conta"
                    lancamento = Lancamento(
                        descricao=txn.description,
                        valor=abs(float(txn.amount)),
                        tipo=tipo,
                        data_transacao=datetime.combine(txn.date, datetime.min.time()),
                        forma_pagamento=nome_banco,  # ✅ Nome real: "Nubank", "Itaú", etc.
                        id_usuario=usuario.id,
                        id_categoria=suggested_category.id if suggested_category else None
                    )
                    
                    db.add(lancamento)
                    
                    # Marcar como importada
                    txn.imported_to_lancamento = True
                    txn.id_lancamento = lancamento.id
                    
                    imported_count += 1
                    
                except Exception as e:
                    logger.error(f"❌ Erro ao importar transação {txn.id}: {e}")
                    continue
            
            db.commit()
            
            message = f"✅ *Importação concluída\\!*\n\n"
            message += f"📊 {imported_count} transação\\(ões\\) importada\\(s\\)\n"
            if skipped_count > 0:
                message += f"⏭️ {skipped_count} pagamento\\(s\\) de fatura ignorado\\(s\\)\n"
            message += f"\nUse /relatorio para ver seus gastos\\."
            
            await query.edit_message_text(message, parse_mode="MarkdownV2")
            
            logger.info(f"✅ {imported_count} transações importadas para usuário {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Erro na importação em massa: {e}", exc_info=True)
            await query.edit_message_text("❌ Erro ao importar transações.")
        finally:
            db.close()
    
    def _suggest_category(self, description: str, merchant_name: str, db):
        """Sugere categoria baseado na descrição e merchant usando IA"""
        from models import Categoria
        import google.generativeai as genai
        from config import GEMINI_API_KEY
        
        # Buscar todas as categorias disponíveis
        categorias = db.query(Categoria).all()
        if not categorias:
            logger.warning("⚠️ Nenhuma categoria encontrada no banco")
            return None
        
        categorias_lista = [cat.nome for cat in categorias]
        
        # Preparar texto para análise
        texto_analise = f"{merchant_name} - {description}" if merchant_name else description
        
        # 🤖 USAR IA PARA CATEGORIZAÇÃO ASSERTIVA
        try:
            genai.configure(api_key=GEMINI_API_KEY)
            model = genai.GenerativeModel('gemini-2.5-flash')  # ✅ Modelo 2.5 (v1beta)
            
            prompt = f"""Você é um especialista em categorização de transações financeiras.

Analise esta transação e escolha a categoria MAIS APROPRIADA:

Transação: "{texto_analise}"

Categorias disponíveis:
{', '.join(categorias_lista)}

REGRAS IMPORTANTES:
- Responda APENAS o nome exato da categoria (sem explicações)
- Se não tiver certeza, escolha a categoria mais próxima
- Exemplos:
  * "IFOOD" → Alimentação
  * "UBER" → Transporte  
  * "NETFLIX" → Lazer
  * "FARMACIA" → Saúde
  * "PIX ENVIADO" → Transferências
  * "TED" → Transferências
  * "SAQUE" → Outros

Categoria escolhida:"""

            response = model.generate_content(prompt)
            categoria_sugerida = response.text.strip()
            
            # Buscar categoria no banco (case-insensitive)
            categoria = db.query(Categoria).filter(
                Categoria.nome.ilike(f"%{categoria_sugerida}%")
            ).first()
            
            if categoria:
                logger.info(f"🤖 IA categorizou '{texto_analise}' como: {categoria.nome}")
                return categoria
            else:
                logger.warning(f"⚠️ IA retornou '{categoria_sugerida}' mas não existe no banco")
                
        except Exception as e:
            logger.error(f"❌ Erro ao usar IA para categorização: {e}")
        
        # 🔄 FALLBACK: Sistema de keywords básico
        desc_lower = description.lower() if description else ""
        merchant_lower = merchant_name.lower() if merchant_name else ""
        
        category_keywords = {
            "Alimentação": ["mercado", "supermercado", "padaria", "açougue", "hortifruti", "ifood", "uber eats", "rappi", "restaurante", "lanchonete", "burger", "pizza"],
            "Transporte": ["uber", "99", "cabify", "posto", "combustível", "gasolina", "etanol", "ipva", "estacionamento", "pedágio"],
            "Lazer": ["netflix", "spotify", "disney", "amazon prime", "cinema", "teatro", "show", "ingresso"],
            "Saúde": ["farmácia", "drogaria", "hospital", "clínica", "médico", "dentista", "laboratorio"],
            "Moradia": ["aluguel", "condomínio", "água", "luz", "energia", "gas", "internet", "iptu"],
            "Compras": ["magazine", "americanas", "mercado livre", "amazon", "shein", "shopee", "loja"],
            "Serviços": ["telefone", "celular", "internet", "tv", "streaming", "assinatura"],
            "Transferências": ["pix", "ted", "doc", "transferencia", "transf"],
            "Outros": ["saque", "tarifa", "taxa"]
        }
        
        for cat_name, keywords in category_keywords.items():
            for keyword in keywords:
                if keyword in desc_lower or keyword in merchant_lower:
                    categoria = db.query(Categoria).filter(Categoria.nome == cat_name).first()
                    if categoria:
                        logger.info(f"💡 Categoria (fallback) para '{description}': {cat_name}")
                        return categoria
        
        # Sem sugestão - retornar "Outros"
        categoria_outros = db.query(Categoria).filter(Categoria.nome == "Outros").first()
        if categoria_outros:
            logger.info(f"📁 Usando categoria padrão 'Outros' para '{description}'")
            return categoria_outros
        
        return None
    
    # ==================== /categorizar - EXTINTOR DE INCÊNDIO 🧯 ====================
    
    async def categorizar_lancamentos(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        🧯 EXTINTOR DE INCÊNDIO - Categoriza automaticamente todos os lançamentos sem categoria
        
        Funciona para lançamentos vindos de:
        - Open Finance (transações importadas)
        - Lançamento Manual
        - OCR (comprovantes escaneados)
        
        Utiliza o Gemini AI para categorização inteligente
        """
        user_id = update.effective_user.id
        logger.info(f"🧯 Usuário {user_id} iniciou categorização automática")
        
        # Mensagem inicial
        status_msg = await update.message.reply_text(
            "🧯 *Extintor de Incêndio Ativado\\!*\n\n"
            "🔍 Buscando lançamentos sem categoria\\.\\.\\.",
            parse_mode="MarkdownV2"
        )
        
        try:
            from database.database import get_db
            from models import Usuario, Lancamento, Categoria
            import google.generativeai as genai
            from config import GEMINI_API_KEY
            
            db = next(get_db())
            
            # Buscar usuário
            usuario = db.query(Usuario).filter(Usuario.telegram_id == user_id).first()
            if not usuario:
                await status_msg.edit_text("❌ Usuário não encontrado\\.", parse_mode="MarkdownV2")
                return
            
            # Buscar lançamentos sem categoria
            lancamentos_sem_categoria = db.query(Lancamento).filter(
                Lancamento.id_usuario == usuario.id,
                Lancamento.id_categoria.is_(None)
            ).all()
            
            if not lancamentos_sem_categoria:
                await status_msg.edit_text(
                    "✅ *Tudo limpo\\!*\n\n"
                    "🎉 Todos os seus lançamentos já estão categorizados\\.",
                    parse_mode="MarkdownV2"
                )
                return
            
            # Configurar Gemini
            genai.configure(api_key=GEMINI_API_KEY)
            model = genai.GenerativeModel('gemini-2.5-flash')  # ✅ Modelo 2.5 (v1beta)
            
            # Buscar categorias disponíveis
            categorias = db.query(Categoria).all()
            categorias_lista = [cat.nome for cat in categorias]
            categorias_dict = {cat.nome.lower(): cat for cat in categorias}
            
            await status_msg.edit_text(
                f"🔥 *Encontrados {len(lancamentos_sem_categoria)} lançamentos sem categoria\\!*\n\n"
                f"🤖 Iniciando categorização em lote com IA\\.\\.\\.\n"
                f"⚡ Modo turbo ativado\\! Processando até 15 por vez\\.",
                parse_mode="MarkdownV2"
            )
            
            # Contadores
            sucesso = 0
            falha = 0
            
            # ⚡ BATCH PROCESSING - Processar em lotes de 15
            BATCH_SIZE = 15
            total_lotes = (len(lancamentos_sem_categoria) + BATCH_SIZE - 1) // BATCH_SIZE
            
            for lote_idx in range(total_lotes):
                inicio = lote_idx * BATCH_SIZE
                fim = min(inicio + BATCH_SIZE, len(lancamentos_sem_categoria))
                lote = lancamentos_sem_categoria[inicio:fim]
                
                try:
                    # Atualizar progresso
                    await status_msg.edit_text(
                        f"🔥 *Categorizando\\.\\.\\.*\n\n"
                        f"📊 Lote {lote_idx + 1}/{total_lotes}\n"
                        f"� Progresso: {fim}/{len(lancamentos_sem_categoria)}\n"
                        f"✅ Sucesso: {sucesso}\n"
                        f"❌ Falhas: {falha}",
                        parse_mode="MarkdownV2"
                    )
                    
                    # Construir prompt em lote
                    transacoes_texto = ""
                    for idx, lanc in enumerate(lote, inicio + 1):
                        transacoes_texto += f"{idx}. Descrição: \"{lanc.descricao}\" | Valor: R$ {abs(lanc.valor):.2f} | Tipo: {'DESPESA' if lanc.tipo == 'despesa' else 'RECEITA'}\n"
                    
                    prompt_batch = f"""Você é um especialista em categorização de transações financeiras.

Analise estas {len(lote)} transações e categorize cada uma de forma CONSISTENTE:

TRANSAÇÕES:
{transacoes_texto}

CATEGORIAS DISPONÍVEIS:
{', '.join(categorias_lista)}

REGRAS IMPORTANTES:
- Analise padrões entre as transações (ex: valores repetidos mensais = assinaturas)
- Seja CONSISTENTE: transações similares devem ter a mesma categoria
- Para PIX/TED/Transferências → "Transferências"
- Para supermercado/feira/padaria → "Alimentação"
- Para Uber/99/combustível/gasolina → "Transporte"
- Para Netflix/Spotify/Disney+/Amazon Prime → "Lazer"
- Para farmácia/médico/hospital → "Saúde"
- Para aluguel/condomínio/luz/água → "Moradia"

FORMATO DE RESPOSTA (uma linha por transação):
1: Nome_da_Categoria
2: Nome_da_Categoria
3: Nome_da_Categoria
...

Categorias:"""
                    
                    # Solicitar categorização ao Gemini (batch)
                    response = model.generate_content(prompt_batch)
                    linhas_resposta = response.text.strip().split('\n')
                    
                    # Processar cada resultado
                    for idx, lanc in enumerate(lote):
                        try:
                            # Encontrar linha correspondente (formato: "1: Categoria" ou "1. Categoria" ou apenas "Categoria")
                            linha = None
                            for l in linhas_resposta:
                                if l.strip().startswith(f"{inicio + idx + 1}:") or l.strip().startswith(f"{inicio + idx + 1}."):
                                    linha = l
                                    break
                            
                            if not linha and idx < len(linhas_resposta):
                                linha = linhas_resposta[idx]
                            
                            if not linha:
                                raise Exception(f"Resposta não encontrada para transação {inicio + idx + 1}")
                            
                            # Extrair categoria (remover número e pontuação)
                            categoria_sugerida = linha.split(':', 1)[-1].split('.', 1)[-1].strip().strip('"').strip("'")
                            
                            # Buscar categoria no banco
                            categoria = categorias_dict.get(categoria_sugerida.lower())
                            
                            if not categoria:
                                # Tentar match parcial
                                for cat_nome, cat_obj in categorias_dict.items():
                                    if categoria_sugerida.lower() in cat_nome or cat_nome in categoria_sugerida.lower():
                                        categoria = cat_obj
                                        break
                            
                            if categoria:
                                lanc.id_categoria = categoria.id
                                sucesso += 1
                                logger.info(f"✅ Lote {lote_idx + 1}: '{lanc.descricao}' → {categoria.nome}")
                            else:
                                # Fallback: categoria "Outros"
                                categoria_outros = categorias_dict.get("outros")
                                if categoria_outros:
                                    lanc.id_categoria = categoria_outros.id
                                    sucesso += 1
                                    logger.warning(f"⚠️ Lote {lote_idx + 1}: '{lanc.descricao}' → Outros (fallback)")
                                else:
                                    falha += 1
                                    logger.error(f"❌ Lote {lote_idx + 1}: Categoria '{categoria_sugerida}' não encontrada para '{lanc.descricao}'")
                        
                        except Exception as e:
                            falha += 1
                            logger.error(f"❌ Lote {lote_idx + 1}: Erro ao categorizar '{lanc.descricao}': {e}")
                    
                except Exception as e:
                    # Erro no lote inteiro - marcar todas como falha
                    falha += len(lote)
                    logger.error(f"❌ Erro ao processar lote {lote_idx + 1}: {e}")
                    continue
            
            # Salvar alterações
            db.commit()
            
            # Mensagem final
            emoji_final = "🎉" if falha == 0 else "✅" if sucesso > 0 else "❌"
            
            message = f"{emoji_final} *Categorização Concluída\\!*\n\n"
            message += f"📊 *Resultados:*\n"
            message += f"✅ Sucesso: {sucesso}\n"
            
            if falha > 0:
                message += f"❌ Falhas: {falha}\n\n"
                message += f"💡 Dica: Lançamentos não categorizados podem ser editados manualmente\\."
            else:
                message += f"\n🎯 Todos os lançamentos foram categorizados com sucesso\\!"
            
            await status_msg.edit_text(message, parse_mode="MarkdownV2")
            
            logger.info(f"🧯 Categorização concluída para usuário {user_id}: {sucesso} sucesso, {falha} falhas")
            
        except Exception as e:
            logger.error(f"❌ Erro na categorização automática: {e}", exc_info=True)
            await status_msg.edit_text(
                "❌ *Erro ao categorizar lançamentos*\n\n"
                "Tente novamente em alguns instantes\\.",
                parse_mode="MarkdownV2"
            )
        finally:
            db.close()
    
    # ==================== CALLBACKS EXTRAS ====================
    
    async def handle_sync_now_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para botão 'Sincronizar Agora' após conectar banco"""
        query = update.callback_query
        await query.answer("🔄 Iniciando sincronização...")
        
        try:
            # Extrair item_id do callback_data
            item_id = query.data.split("_")[-1]
            user_id = update.effective_user.id
            
            # Mensagem de progresso
            await query.edit_message_text(
                "🔄 *Sincronizando dados\\.\\.\\.*\n\n"
                "Isso pode levar alguns segundos\\.\\.\\.",
                parse_mode="MarkdownV2"
            )
            
            # Realizar sincronização
            result = sync_all_transactions_for_user(user_id)
            
            if "error" in result:
                await query.edit_message_text(
                    f"❌ *Erro na sincronização*\n\n"
                    f"Detalhes: {result['error']}",
                    parse_mode="Markdown"
                )
                return
            
            # Sucesso
            await query.edit_message_text(
                f"✅ *Sincronização Concluída\\!*\n\n"
                f"📊 *Resultados:*\n"
                f"💳 {result.get('accounts', 0)} conta\\(s\\)\n"
                f"📝 {result.get('new', 0)} nova\\(s\\) transação\\(ões\\)\n"
                f"🔄 {result.get('updated', 0)} atualizada\\(s\\)\n\n"
                f"Use /minhas\\_contas para ver os detalhes\\!",
                parse_mode="MarkdownV2"
            )
            
        except Exception as e:
            logger.error(f"❌ Erro no callback de sincronização: {e}", exc_info=True)
            await query.edit_message_text(
                "❌ Erro ao sincronizar dados\\.\n\n"
                "Tente usar o comando /sincronizar\\.",
                parse_mode="MarkdownV2"
            )
    
    async def handle_view_accounts_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para botão 'Ver Contas' após conectar banco"""
        query = update.callback_query
        await query.answer()
        
        # Redirecionar para o comando /minhas_contas
        await self.minhas_contas(update, context)
    
    # ==================== /debug_open_finance ====================
    
    async def debug_open_finance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando DEBUG: Mostra detalhes técnicos das conexões Open Finance"""
        user_id = update.effective_user.id
        
        logger.info(f"🔍 DEBUG: Usuário {user_id} solicitando debug Open Finance")
        
        # 🔐 VERIFICAR WHITELIST
        from config import PLUGGY_WHITELIST_IDS
        if PLUGGY_WHITELIST_IDS and user_id not in PLUGGY_WHITELIST_IDS:
            await update.message.reply_text("🔒 Funcionalidade restrita.")
            return
        
        try:
            from database.database import get_db
            from models import Usuario, PluggyItem, PluggyAccount, Investment
            
            db = next(get_db())
            
            # Buscar usuário
            usuario = db.query(Usuario).filter(Usuario.telegram_id == user_id).first()
            if not usuario:
                await update.message.reply_text("❌ Usuário não encontrado.")
                return
            
            # Buscar itens conectados
            items = db.query(PluggyItem).filter(PluggyItem.id_usuario == usuario.id).all()
            
            if not items:
                await update.message.reply_text("❌ Nenhum banco conectado.")
                return
            
            message = "🔍 *DEBUG: Open Finance*\n\n"
            
            for item in items:
                message += f"━━━━━━━━━━━━━━━━\n"
                message += f"🏦 *{item.connector_name}*\n"
                message += f"📋 Item ID: `{item.pluggy_item_id}`\n"
                message += f"📅 Status: {item.status}\n"
                message += f"🕐 Conectado: {item.created_at.strftime('%d/%m/%Y %H:%M')}\n\n"
                
                # Buscar contas deste item
                accounts = db.query(PluggyAccount).filter(PluggyAccount.id_item == item.id).all()
                message += f"💳 *Contas ({len(accounts)}):*\n"
                
                for acc in accounts:
                    # Detectar se pode ser investimento
                    nome_lower = (acc.name or "").lower()
                    is_possible_investment = any(word in nome_lower for word in ["cofrinho", "cofre", "investimento", "poupança", "savings"])
                    
                    emoji = "💰" if is_possible_investment else "  •"
                    message += f"{emoji} {acc.name}\n"
                    message += f"    Tipo: `{acc.type}`"
                    
                    if is_possible_investment and acc.type != "INVESTMENT":
                        message += f" ⚠️ _Pode ser investimento!_"
                    
                    message += f"\n    Subtipo: `{acc.subtype or 'N/A'}`\n"
                    message += f"    Saldo: R$ {acc.balance or 0:.2f}\n"
                    if acc.credit_limit:
                        message += f"    Limite: R$ {acc.credit_limit:.2f}\n"
                    message += "\n"
                
                # Buscar investimentos via endpoint direto
                try:
                    inv_data = pluggy_request("GET", "/investments", params={"itemId": item.pluggy_item_id})
                    inv_results = inv_data.get("results", [])
                    
                    message += f"📈 *Investimentos (Endpoint /investments):* {len(inv_results)}\n"
                    if inv_results:
                        for inv in inv_results[:3]:  # Mostrar até 3
                            message += f"  • {inv.get('name', 'N/A')}\n"
                            message += f"    Valor: R$ {inv.get('balance', 0):.2f}\n"
                    else:
                        message += "  ℹ️ Nenhum investimento retornado pelo endpoint específico\n"
                except Exception as e:
                    message += f"  ⚠️ Erro ao buscar: {str(e)[:50]}\n"
                
                message += "\n"
            
            # Investimentos salvos no banco
            investments = db.query(Investment).filter(
                Investment.id_usuario == usuario.id,
                Investment.ativo == True,
                Investment.fonte == "PLUGGY"
            ).all()
            
            message += f"━━━━━━━━━━━━━━━━\n"
            message += f"💎 *Investimentos Detectados (Total):* {len(investments)}\n"
            for inv in investments:
                message += f"  • {inv.nome}\n"
                message += f"    Tipo: {inv.tipo}\n"
                message += f"    Valor: R$ {inv.valor_atual:.2f}\n"
            
            await update.message.reply_text(message, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"❌ Erro no debug: {e}", exc_info=True)
            await update.message.reply_text(f"❌ Erro: {e}")
    
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
