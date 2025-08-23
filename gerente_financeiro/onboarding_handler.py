# gerente_financeiro/onboarding_handler.py
import logging
from datetime import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler, CallbackQueryHandler, MessageHandler, filters
)

# Importar analytics
try:
    from analytics.bot_analytics import BotAnalytics
    analytics = BotAnalytics()
    ANALYTICS_ENABLED = True
except ImportError:
    ANALYTICS_ENABLED = False

def track_analytics(command_name):
    """Decorator para tracking de comandos"""
    import functools
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(update, context):
            if ANALYTICS_ENABLED and update.effective_user:
                user_id = update.effective_user.id
                username = update.effective_user.username or update.effective_user.first_name or "Usuário"
                
                try:
                    analytics.track_command_usage(
                        user_id=user_id,
                        username=username,
                        command=command_name,
                        success=True
                    )
                    analytics.track_daily_user(user_id, username, command_name)
                    logging.info(f"📊 Analytics: {username} usou /{command_name}")
                except Exception as e:
                    logging.error(f"❌ Erro no analytics: {e}")
            
            return await func(update, context)
        return wrapper
    return decorator

from database.database import get_db, get_or_create_user # <-- Importação adicionada
from models import Usuario, Conta
from .handlers import cancel
from .states import (
    MENU_PRINCIPAL, ADD_CONTA_NOME, ASK_ADD_ANOTHER_CONTA,  
    ADD_CARTAO_NOME, ADD_CARTAO_FECHAMENTO, ADD_CARTAO_VENCIMENTO, ADD_CARTAO_LIMITE, ASK_ADD_ANOTHER_CARTAO, 
    ASK_HORARIO, PERFIL_ASK_RISCO, PERFIL_ASK_OBJETIVO, PERFIL_ASK_HABITO,
    GERENCIAR_CONTAS, GERENCIAR_CARTOES
)

logger = logging.getLogger(__name__)

# --- FUNÇÕES DE MENU E NAVEGAÇÃO ---

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Exibe o menu principal de configuração de forma consistente."""
    query = update.callback_query
    effective_user = update.effective_user
    if query:
        effective_user = query.from_user
    
    db = next(get_db())
    # Usamos get_or_create_user para garantir que o usuário sempre exista
    user_db = get_or_create_user(db, effective_user.id, effective_user.full_name)
    horario_atual = user_db.horario_notificacao.strftime('%H:%M') if user_db.horario_notificacao else "09:00"
    perfil_atual = user_db.perfil_investidor if user_db.perfil_investidor else "Não definido"
    db.close()

    text = (
        f"🎯 <b>Painel de Configuração Financeira</b>\n\n"
        f"⏰ Horário dos lembretes: <b>{horario_atual}</b>\n"
        f"📊 Perfil de investidor: <b>{'❌ Ainda não definido' if perfil_atual == 'Não definido' else perfil_atual}</b>\n\n"
        "✨ Personalize sua experiência com os botões abaixo:"
    )
    keyboard = [
        [InlineKeyboardButton("👤 Gerenciar Perfil de Investidor", callback_data="config_perfil")],
        [InlineKeyboardButton("🏦 Gerenciar Contas", callback_data="config_contas")],
        [InlineKeyboardButton("💳 Gerenciar Cartões", callback_data="config_cartoes")],
        [InlineKeyboardButton("⏰ Alterar Horário de Lembretes", callback_data="config_horario")],
        [InlineKeyboardButton("✅ Concluir", callback_data="config_concluir")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if query:
        await query.edit_message_text(text, parse_mode='HTML', reply_markup=reply_markup)
    else:
        await update.message.reply_html(text, reply_markup=reply_markup)
    
    return MENU_PRINCIPAL

# --- FLUXO PRINCIPAL ---

@track_analytics("start")
async def start_onboarding(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Função específica para /start - inclui saudação de boas-vindas."""
    # Garante que o usuário exista no banco de dados
    db = next(get_db())
    try:
        user = get_or_create_user(db, update.effective_user.id, update.effective_user.full_name)
        user_name = user.nome_completo.split(' ')[0] if user.nome_completo else update.effective_user.first_name
        
        # Saudação especial para /start
        welcome_text = (
            f"👋 <b>Olá, {user_name}!</b>\n\n"
            "Para que eu possa ser seu melhor assistente financeiro, "
            "precisamos configurar seu ecossistema.\n\n"
            "📋 <b>Esta etapa é rápida e vai me ajudar a personalizar sua "
            "experiência do seu jeito.</b>\n\n"
            "Se quiser explorar tudo que posso fazer, digite /help. 🚀"
        )
        
        await update.message.reply_html(welcome_text)
        
        # Vai direto para o menu principal
        return await show_main_menu(update, context)
        
    finally:
        db.close()

async def configurar_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Função específica para /configurar - vai direto ao menu sem saudação."""
    # Garante que o usuário exista no banco de dados
    db = next(get_db())
    try:
        user = get_or_create_user(db, update.effective_user.id, update.effective_user.full_name)
        
        # Vai direto para o menu principal sem saudação
        return await show_main_menu(update, context)
        
    finally:
        db.close()

@track_analytics("menu")
async def menu_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Processa os cliques nos botões do menu principal."""
    query = update.callback_query
    await query.answer()
    action = query.data.split('_')[1]

    if action == "concluir":
        await query.edit_message_text("✅ Configurações salvas!", reply_markup=None)
        return ConversationHandler.END

    if action == "perfil":
        return await start_perfil_flow(update, context)

    if action == "contas":
        return await show_gerenciar_contas(update, context)
        
    if action == "cartoes":
        return await show_gerenciar_cartoes(update, context)
        
    if action == "horario":
        await query.edit_message_text(
            "📆 Por favor, digite o horário em que deseja receber seus lembretes diários.\n\n"
            "Use o formato <b>24h (HH:MM)</b>, por exemplo: <b>08:30</b>",
            parse_mode='HTML'
        )
        return ASK_HORARIO

# --- FLUXO DE PERFIL DE INVESTIDOR ---

async def start_perfil_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['perfil_pontos'] = 0
    text = (
        "<b>Pergunta 1 de 3: Tolerância ao Risco</b>\n\n"
        "Se seus investimentos caíssem 20% em um mês, o que você faria?"
    )
    keyboard = [
        [InlineKeyboardButton("A) Venderia tudo para evitar mais perdas", callback_data="perfil_risco_1")],
        [InlineKeyboardButton("B) Esperaria o mercado se recuperar", callback_data="perfil_risco_2")],
        [InlineKeyboardButton("C) Aproveitaria para comprar mais", callback_data="perfil_risco_3")]
    ]
    await update.callback_query.edit_message_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))
    return PERFIL_ASK_RISCO

async def ask_perfil_risco(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    pontos = int(query.data.split('_')[-1])
    context.user_data['perfil_pontos'] += pontos
    text = (
        "<b>Pergunta 2 de 3: Objetivo Principal</b>\n\n"
        "Qual é seu principal objetivo com o dinheiro investido?"
    )
    keyboard = [
        [InlineKeyboardButton("A) Segurança e proteção do capital", callback_data="perfil_objetivo_1")],
        [InlineKeyboardButton("B) Crescimento estável no médio prazo", callback_data="perfil_objetivo_2")],
        [InlineKeyboardButton("C) Alto retorno no longo prazo, mesmo com riscos", callback_data="perfil_objetivo_3")]
    ]
    await query.edit_message_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))
    return PERFIL_ASK_OBJETIVO

async def ask_perfil_objetivo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    pontos = int(query.data.split('_')[-1])
    context.user_data['perfil_pontos'] += pontos
    text = (
        "<b>Pergunta 3 de 3: Hábito Financeiro</b>\n\n"
        "Você costuma guardar dinheiro todos os meses?"
    )
    keyboard = [
        [InlineKeyboardButton("A) Sim, com disciplina", callback_data="perfil_habito_3")],
        [InlineKeyboardButton("B) Só quando sobra", callback_data="perfil_habito_2")],
        [InlineKeyboardButton("C) Quase nunca consigo guardar", callback_data="perfil_habito_1")]
    ]
    await query.edit_message_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))
    return PERFIL_ASK_HABITO

async def finalizar_perfil(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    pontos = int(query.data.split('_')[-1])
    total_pontos = context.user_data.get('perfil_pontos', 0) + pontos

    if total_pontos <= 4: perfil = 'Conservador'
    elif total_pontos <= 7: perfil = 'Moderado'
    else: perfil = 'Arrojado'
    
    db = next(get_db())
    try:
        # A consulta agora vai funcionar, pois o usuário foi criado no início
        user_db = db.query(Usuario).filter(Usuario.telegram_id == query.from_user.id).first()
        user_db.perfil_investidor = perfil
        db.commit()
        await query.edit_message_text(f"✅ Perfil definido como: <b>{perfil}</b>!\n\nRetornando ao menu...", parse_mode='HTML', reply_markup=None)
    finally:
        db.close()
        context.user_data.pop('perfil_pontos', None)
    
    import asyncio
    await asyncio.sleep(1.5)
    return await show_main_menu(update, context)

# --- GERENCIAMENTO DE CONTAS ---

async def show_gerenciar_contas(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Exibe lista de contas existentes com opções de gerenciamento."""
    query = update.callback_query
    user_id = query.from_user.id
    
    db = next(get_db())
    try:
        # Buscar contas do usuário (apenas do tipo "Conta")
        usuario_db = db.query(Usuario).filter(Usuario.telegram_id == user_id).first()
        contas = db.query(Conta).filter(
            Conta.id_usuario == usuario_db.id,
            Conta.tipo == "Conta"
        ).all()
        
        if not contas:
            # Nenhuma conta cadastrada
            text = (
                "🏦 <b>Gerenciar Contas</b>\n\n"
                "📝 Você ainda não tem contas cadastradas.\n"
                "Vamos cadastrar sua primeira conta agora!"
            )
            keyboard = [
                [InlineKeyboardButton("➕ Adicionar Primeira Conta", callback_data="add_new_conta")],
                [InlineKeyboardButton("⬅️ Voltar ao Menu", callback_data="voltar_menu")]
            ]
        else:
            # Exibir contas existentes
            text = "🏦 <b>Suas Contas Cadastradas</b>\n\n"
            keyboard = []
            
            for conta in contas:
                text += f"💰 <b>{conta.nome}</b>\n"
                # Botão para excluir conta específica
                keyboard.append([
                    InlineKeyboardButton(f"🗑️ Excluir {conta.nome}", callback_data=f"delete_conta_{conta.id}")
                ])
            
            text += "\n💡 <i>Escolha uma ação:</i>"
            keyboard.extend([
                [InlineKeyboardButton("➕ Adicionar Nova Conta", callback_data="add_new_conta")],
                [InlineKeyboardButton("⬅️ Voltar ao Menu", callback_data="voltar_menu")]
            ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, parse_mode='HTML', reply_markup=reply_markup)
        return GERENCIAR_CONTAS
        
    finally:
        db.close()

async def show_gerenciar_cartoes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Exibe lista de cartões existentes com opções de gerenciamento."""
    query = update.callback_query
    user_id = query.from_user.id
    
    db = next(get_db())
    try:
        # Buscar cartões do usuário (apenas do tipo "Cartão de Crédito")
        usuario_db = db.query(Usuario).filter(Usuario.telegram_id == user_id).first()
        cartoes = db.query(Conta).filter(
            Conta.id_usuario == usuario_db.id,
            Conta.tipo == "Cartão de Crédito"
        ).all()
        
        if not cartoes:
            # Nenhum cartão cadastrado
            text = (
                "💳 <b>Gerenciar Cartões</b>\n\n"
                "📝 Você ainda não tem cartões cadastrados.\n"
                "Vamos cadastrar seu primeiro cartão agora!"
            )
            keyboard = [
                [InlineKeyboardButton("➕ Adicionar Primeiro Cartão", callback_data="add_new_cartao")],
                [InlineKeyboardButton("⬅️ Voltar ao Menu", callback_data="voltar_menu")]
            ]
        else:
            # Exibir cartões existentes
            text = "💳 <b>Seus Cartões Cadastrados</b>\n\n"
            keyboard = []
            
            for cartao in cartoes:
                text += f"💳 <b>{cartao.nome}</b>\n"
                
                # Verificar se os campos não são None antes de formatar
                if cartao.limite_cartao is not None:
                    text += f"   💰 Limite: R$ {cartao.limite_cartao:.2f}\n"
                else:
                    text += f"   💰 Limite: ⚠️ <i>Não definido</i>\n"
                
                if cartao.dia_fechamento is not None:
                    text += f"   📅 Fechamento: dia {cartao.dia_fechamento}\n"
                else:
                    text += f"   📅 Fechamento: ⚠️ <i>Não definido</i>\n"
                
                if cartao.dia_vencimento is not None:
                    text += f"   �️ Vencimento: dia {cartao.dia_vencimento}\n\n"
                else:
                    text += f"   🗓️ Vencimento: ⚠️ <i>Não definido</i>\n\n"
                
                # Botão para excluir cartão específico
                keyboard.append([
                    InlineKeyboardButton(f"🗑️ Excluir {cartao.nome}", callback_data=f"delete_cartao_{cartao.id}")
                ])
            
            text += "💡 <i>Escolha uma ação:</i>"
            keyboard.extend([
                [InlineKeyboardButton("➕ Adicionar Novo Cartão", callback_data="add_new_cartao")],
                [InlineKeyboardButton("⬅️ Voltar ao Menu", callback_data="voltar_menu")]
            ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, parse_mode='HTML', reply_markup=reply_markup)
        return GERENCIAR_CARTOES
        
    finally:
        db.close()

async def handle_gerenciar_contas_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Processa callbacks do gerenciamento de contas."""
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data == "add_new_conta":
        await query.edit_message_text(
            "🏦 <b>Nova Conta</b>\n\n"
            "Qual o nome da conta que deseja adicionar?\n"
            "<i>(ex: Itaú, Nubank, Bradesco, C6 Bank)</i>",
            parse_mode='HTML'
        )
        return ADD_CONTA_NOME
        
    elif data.startswith("delete_conta_"):
        conta_id = int(data.split("_")[-1])
        
        # Confirmar exclusão
        keyboard = [
            [InlineKeyboardButton("✅ Sim, excluir", callback_data=f"confirm_delete_conta_{conta_id}")],
            [InlineKeyboardButton("❌ Cancelar", callback_data="cancelar_exclusao_conta")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⚠️ <b>Confirmar Exclusão</b>\n\n"
            "Tem certeza que deseja excluir esta conta?\n\n"
            "⚠️ <i>Atenção: Lançamentos vinculados a esta conta não serão excluídos, "
            "mas ficarão sem conta associada.</i>",
            parse_mode='HTML',
            reply_markup=reply_markup
        )
        return GERENCIAR_CONTAS
        
    elif data.startswith("confirm_delete_conta_"):
        conta_id = int(data.split("_")[-1])
        user_id = query.from_user.id
        
        db = next(get_db())
        try:
            # Verificar se a conta pertence ao usuário
            usuario_db = db.query(Usuario).filter(Usuario.telegram_id == user_id).first()
            conta = db.query(Conta).filter(
                Conta.id == conta_id,
                Conta.id_usuario == usuario_db.id
            ).first()
            
            if conta:
                conta_nome = conta.nome
                db.delete(conta)
                db.commit()
                
                await query.edit_message_text(
                    f"✅ <b>Conta '{conta_nome}' excluída com sucesso!</b>\n\n"
                    "Retornando ao gerenciamento de contas...",
                    parse_mode='HTML'
                )
                
                import asyncio
                await asyncio.sleep(1.5)
                return await show_gerenciar_contas(update, context)
            else:
                await query.edit_message_text("❌ Erro: Conta não encontrada.")
                return GERENCIAR_CONTAS
                
        finally:
            db.close()
            
    elif data == "cancelar_exclusao_conta":
        return await show_gerenciar_contas(update, context)
        
    elif data == "voltar_menu":
        return await show_main_menu(update, context)

async def handle_gerenciar_cartoes_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Processa callbacks do gerenciamento de cartões."""
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data == "add_new_cartao":
        await query.edit_message_text(
            "💳 <b>Novo Cartão</b>\n\n"
            "Qual o nome do cartão que deseja adicionar?\n"
            "<i>(ex: Inter Gold, Nubank Roxinho, C6 Carbon)</i>",
            parse_mode='HTML'
        )
        return ADD_CARTAO_NOME
        
    elif data.startswith("delete_cartao_"):
        cartao_id = int(data.split("_")[-1])
        
        # Confirmar exclusão
        keyboard = [
            [InlineKeyboardButton("✅ Sim, excluir", callback_data=f"confirm_delete_cartao_{cartao_id}")],
            [InlineKeyboardButton("❌ Cancelar", callback_data="cancelar_exclusao_cartao")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⚠️ <b>Confirmar Exclusão</b>\n\n"
            "Tem certeza que deseja excluir este cartão?\n\n"
            "⚠️ <i>Atenção: Lançamentos vinculados a este cartão não serão excluídos, "
            "mas ficarão sem cartão associado.</i>",
            parse_mode='HTML',
            reply_markup=reply_markup
        )
        return GERENCIAR_CARTOES
        
    elif data.startswith("confirm_delete_cartao_"):
        cartao_id = int(data.split("_")[-1])
        user_id = query.from_user.id
        
        db = next(get_db())
        try:
            # Verificar se o cartão pertence ao usuário
            usuario_db = db.query(Usuario).filter(Usuario.telegram_id == user_id).first()
            cartao = db.query(Conta).filter(
                Conta.id == cartao_id,
                Conta.id_usuario == usuario_db.id
            ).first()
            
            if cartao:
                cartao_nome = cartao.nome
                db.delete(cartao)
                db.commit()
                
                await query.edit_message_text(
                    f"✅ <b>Cartão '{cartao_nome}' excluído com sucesso!</b>\n\n"
                    "Retornando ao gerenciamento de cartões...",
                    parse_mode='HTML'
                )
                
                import asyncio
                await asyncio.sleep(1.5)
                return await show_gerenciar_cartoes(update, context)
            else:
                await query.edit_message_text("❌ Erro: Cartão não encontrado.")
                return GERENCIAR_CARTOES
                
        finally:
            db.close()
            
    elif data == "cancelar_exclusao_cartao":
        return await show_gerenciar_cartoes(update, context)
        
    elif data == "voltar_menu":
        return await show_main_menu(update, context)

# --- OUTROS SUB-FLUXOS ---

async def add_conta_nome(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    nome_conta = update.message.text
    db = next(get_db())
    try:
        usuario_db = db.query(Usuario).filter(Usuario.telegram_id == update.effective_user.id).first()
        nova_conta = Conta(id_usuario=usuario_db.id, nome=nome_conta, tipo="Conta")
        db.add(nova_conta)
        db.commit()
        # Em vez de voltar ao menu, perguntamos se o usuário quer adicionar outra conta.
        keyboard = [
            [InlineKeyboardButton("➕ Sim, adicionar outra", callback_data="add_another_conta_sim")],
            [InlineKeyboardButton("⬅️ Não, voltar ao menu", callback_data="add_another_conta_nao")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_html(
            f"✅ Conta '<b>{nome_conta}</b>' adicionada!\n\nDeseja adicionar outra conta?",
            reply_markup=reply_markup
        )

        
        return ASK_ADD_ANOTHER_CONTA
 
    finally:
        db.close()

async def add_cartao_nome(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['novo_cartao_nome'] = update.message.text
    await update.message.reply_html("🗓️ Qual o <b>dia de fechamento</b> da fatura? <b>(Apenas o número)</b>")
    return ADD_CARTAO_FECHAMENTO

async def add_cartao_fechamento(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        context.user_data['novo_cartao_fechamento'] = int(update.message.text)
        await update.message.reply_html("🗓️ E qual o <b>dia de vencimento</b> da fatura?")
        return ADD_CARTAO_VENCIMENTO
    except (ValueError, TypeError):
        await update.message.reply_text("⚠️ Por favor, insira um número válido.")
        return ADD_CARTAO_FECHAMENTO

async def add_cartao_vencimento(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        context.user_data['novo_cartao_vencimento'] = int(update.message.text)
        await update.message.reply_html("💳 Qual o <b>limite total</b> do cartão? <b>(Exemplo: 5000.00)</b>")
        return ADD_CARTAO_LIMITE
    except (ValueError, TypeError):
        await update.message.reply_text("⚠️ Por favor, insira um número válido.")
        return ADD_CARTAO_VENCIMENTO

async def add_cartao_limite(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    texto = update.message.text.strip().replace(',', '.')
    try:
        limite = float(texto)
        nome_cartao = context.user_data['novo_cartao_nome']
        dia_fechamento = context.user_data['novo_cartao_fechamento']
        dia_vencimento = context.user_data['novo_cartao_vencimento']
        
        db = next(get_db())
        try:
            usuario_db = db.query(Usuario).filter(Usuario.telegram_id == update.effective_user.id).first()
            novo_cartao = Conta(
                id_usuario=usuario_db.id, 
                nome=nome_cartao, 
                tipo="Cartão de Crédito",
                dia_fechamento=dia_fechamento, 
                dia_vencimento=dia_vencimento,
                limite_cartao=limite
            )
            db.add(novo_cartao)
            db.commit()
            
            # Pergunta se quer adicionar outro cartão
            keyboard = [
                [InlineKeyboardButton("➕ Sim, adicionar outro", callback_data="add_another_cartao_sim")],
                [InlineKeyboardButton("⬅️ Não, voltar ao menu", callback_data="add_another_cartao_nao")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_html(
                f"✅ Cartão <b>{nome_cartao}</b> adicionado com sucesso!\n"
                f"💳 Limite: R$ {limite:.2f}\n"
                f"📅 Fechamento: dia {dia_fechamento}\n"
                f"🗓️ Vencimento: dia {dia_vencimento}\n\n"
                f"Deseja adicionar outro cartão de crédito?",
                reply_markup=reply_markup
            )
            
            return ASK_ADD_ANOTHER_CARTAO

        finally:
            db.close()
            # Limpar dados temporários
            for key in ['novo_cartao_nome', 'novo_cartao_fechamento', 'novo_cartao_vencimento']:
                context.user_data.pop(key, None)

    except (ValueError, TypeError):
        await update.message.reply_text("⚠️ Valor inválido. Por favor, digite apenas números e ponto. (Exemplo: 5000.00)")
        return ADD_CARTAO_LIMITE

async def handle_add_another_cartao(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Processa a decisão de adicionar ou não outro cartão."""
    query = update.callback_query
    await query.answer()
    action = query.data

    if action == "add_another_cartao_sim":
        # Se sim, voltamos para o início do fluxo de cartão.
        await query.edit_message_text("Ok! Qual o nome do próximo cartão? (ex: XP Visa Infinite)", parse_mode='HTML')
        return ADD_CARTAO_NOME
    else: # "add_another_cartao_nao"
        # Se não, voltamos para o gerenciamento de cartões (não menu principal)
        return await show_gerenciar_cartoes(update, context)
    
async def handle_add_another_conta(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Processa a decisão de adicionar ou não outra conta."""
    query = update.callback_query
    await query.answer()
    action = query.data

    if action == "add_another_conta_sim":
        # Se sim, apenas pedimos o nome da próxima conta e voltamos ao estado ADD_CONTA_NOME.
        await query.edit_message_text("🏦 Beleza! Manda o nome da próxima <b>conta</b>?", parse_mode='HTML')
        return ADD_CONTA_NOME
    else: # "add_another_conta_nao"
        # Se não, voltamos para o gerenciamento de contas (não menu principal)
        return await show_gerenciar_contas(update, context)

async def save_horario(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        novo_horario_obj = time.fromisoformat(update.message.text)
        db = next(get_db())
        try:
            user_db = db.query(Usuario).filter(Usuario.telegram_id == update.effective_user.id).first()
            user_db.horario_notificacao = novo_horario_obj
            db.commit()
            await update.message.reply_html(f"✅ Horário de lembretes atualizado para <b>{update.message.text}</b>.")
        finally:
            db.close()
        return await show_main_menu(update, context)
    except ValueError:
        await update.message.reply_text("⚠️ Formato inválido. Use HH:MM (ex: 09:00).")
        return ASK_HORARIO

# --- CONVERSATION HANDLER UNIFICADO ---
configurar_conv = ConversationHandler(
    entry_points=[
        CommandHandler('configurar', configurar_start),  # Vai direto ao menu
        CommandHandler('start', start_onboarding)        # Inclui saudação de boas-vindas
    ],
    states={
        MENU_PRINCIPAL: [CallbackQueryHandler(menu_callback_handler, pattern='^config_')],
        
        # --- GERENCIAMENTO DE CONTAS ---
        GERENCIAR_CONTAS: [CallbackQueryHandler(handle_gerenciar_contas_callback)],
        
        # --- GERENCIAMENTO DE CARTÕES ---
        GERENCIAR_CARTOES: [CallbackQueryHandler(handle_gerenciar_cartoes_callback)],
        
        # ---FLUXO DE CONTAS ---
        ADD_CONTA_NOME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_conta_nome)],
        ASK_ADD_ANOTHER_CONTA: [CallbackQueryHandler(handle_add_another_conta, pattern='^add_another_conta_')],

        # ---FLUXO DE CARTÕES ---
        ADD_CARTAO_NOME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_cartao_nome)],
        ADD_CARTAO_FECHAMENTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_cartao_fechamento)],
        ADD_CARTAO_VENCIMENTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_cartao_vencimento)],
        ADD_CARTAO_LIMITE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_cartao_limite)],
        ASK_ADD_ANOTHER_CARTAO: [CallbackQueryHandler(handle_add_another_cartao, pattern='^add_another_cartao_')],

        # --- OUTROS ESTADOS ---
        ASK_HORARIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_horario)],
        PERFIL_ASK_RISCO: [CallbackQueryHandler(ask_perfil_risco, pattern='^perfil_risco_')],
        PERFIL_ASK_OBJETIVO: [CallbackQueryHandler(ask_perfil_objetivo, pattern='^perfil_objetivo_')],
        PERFIL_ASK_HABITO: [CallbackQueryHandler(finalizar_perfil, pattern='^perfil_habito_')],
    },
    fallbacks=[CommandHandler('cancelar', cancel)],
    per_message=False,  # False porque mistura MessageHandler e CallbackQueryHandler
    per_user=True,
    per_chat=True
)