import logging
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler, CommandHandler, ContextTypes, ConversationHandler,
    MessageHandler, filters
)

from database.database import get_db, get_or_create_user
from models import Categoria, Agendamento, Usuario
from .handlers import cancel, criar_teclado_colunas
from .utils_validation import (
    validar_valor_monetario, validar_descricao,
    ask_valor_generico, ask_descricao_generica
)
from .states import (
    ASK_TIPO, ASK_DESCRICAO_AGENDAMENTO, ASK_VALOR_AGENDAMENTO, ASK_CATEGORIA_AGENDAMENTO, 
    ASK_PRIMEIRO_EVENTO, ASK_FREQUENCIA, ASK_TIPO_RECORRENCIA, ASK_TOTAL_PARCELAS, 
    CONFIRM_AGENDAMENTO
)
from typing import List
from .messages import render_message

logger = logging.getLogger(__name__)

# --- ENTRYPOINT / MENU INICIAL ---
async def agendamento_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entrypoint: inicia fluxo pedindo o tipo (Entrada/Saída)."""
    query = update.callback_query
    await query.answer()
    # Inicia estrutura de dados do novo agendamento
    context.user_data['novo_agendamento'] = {}
    keyboard = [[
        InlineKeyboardButton("🟢 Entrada", callback_data="ag_tipo_Entrada"),
        InlineKeyboardButton("🔴 Saída", callback_data="ag_tipo_Saida")
    ]]
    texto = f"{render_message('ag_novo_titulo')}\n\n{render_message('ag_pergunta_tipo')}"
    await query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
    return ASK_TIPO

 # Funções refatoradas abaixo

# --- FLUXO DE CRIAÇÃO MODERNO ---
async def ask_tipo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Processa tipo e vai para descrição com visual moderno"""
    query = update.callback_query
    await query.answer()
    
    tipo = query.data.split('_')[-1]
    context.user_data['novo_agendamento']['tipo'] = tipo
    
    emoji = "🟢" if tipo == "Entrada" else "🔴"
    
    await query.edit_message_text(
        render_message("ag_prompt_descricao", emoji=emoji, tipo=tipo),
        parse_mode='HTML'
    )
    return ASK_DESCRICAO_AGENDAMENTO

async def ask_descricao(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Processa a descrição e vai para o valor com visual moderno"""
    descricao_texto = update.message.text.strip()
    
    # Validação simples de descrição
    if len(descricao_texto) < 2 or len(descricao_texto) > 200:
        await update.message.reply_text(render_message("ag_descricao_invalida"), parse_mode='HTML')
        return ASK_DESCRICAO_AGENDAMENTO
    
    # Salva a descrição
    context.user_data['novo_agendamento']['descricao'] = descricao_texto
    
    # Pergunta o valor de forma mais atrativa
    tipo = context.user_data['novo_agendamento']['tipo']
    emoji = "🟢" if tipo == "Entrada" else "🔴"
    
    await update.message.reply_text(
        render_message("ag_prompt_valor", emoji=emoji, descricao=descricao_texto),
        parse_mode='HTML'
    )
    
    return ASK_VALOR_AGENDAMENTO

async def ask_valor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Processa o valor e vai para seleção de categoria"""
    # Validação mais robusta do valor
    valor_texto = update.message.text.strip().replace('R$', '').replace(' ', '').replace(',', '.')
    
    try:
        valor = float(valor_texto)
        if valor <= 0:
            raise ValueError("Valor deve ser positivo")
    except ValueError:
        await update.message.reply_text(render_message("ag_valor_invalido"), parse_mode='HTML')
        return ASK_VALOR_AGENDAMENTO
    
    # Salva o valor
    context.user_data['novo_agendamento']['valor'] = valor
    
    # Busca categorias
    db = next(get_db())
    try:
        categorias = db.query(Categoria).order_by(Categoria.nome).all()
        
        # Cria botões para categorias
        botoes = []
        for categoria in categorias:
            botoes.append(InlineKeyboardButton(
                categoria.nome, 
                callback_data=f"ag_cat_{categoria.id}"
            ))
        
        # Adiciona opção "Sem categoria"
        botoes.append(InlineKeyboardButton("🏷️ Sem Categoria", callback_data="ag_cat_0"))
        
        teclado = criar_teclado_colunas(botoes, 2)
        
        # Resumo do que foi preenchido
        dados = context.user_data['novo_agendamento']
        tipo = dados['tipo']
        emoji_tipo = "🟢" if tipo == "Entrada" else "🔴"
        await update.message.reply_text(
            render_message("ag_resumo_categoria_prompt", emoji=emoji_tipo, descricao=dados['descricao'], valor=valor),
            reply_markup=InlineKeyboardMarkup(teclado),
            parse_mode='HTML'
        )
        
        return ASK_CATEGORIA_AGENDAMENTO
        
    finally:
        db.close()

async def ask_categoria(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Processa categoria e vai para primeira data"""
    query = update.callback_query
    await query.answer()
    
    category_id = int(query.data.split('_')[-1])
    context.user_data['novo_agendamento']['id_categoria'] = category_id if category_id != 0 else None
    
    # Busca nome da categoria
    categoria_nome = "Sem categoria"
    if category_id != 0:
        db = next(get_db())
        try:
            categoria = db.query(Categoria).filter(Categoria.id == category_id).first()
            if categoria:
                categoria_nome = categoria.nome
        finally:
            db.close()
    
    # Resumo e pergunta da primeira data
    dados = context.user_data['novo_agendamento']
    tipo = dados['tipo']
    emoji_tipo = "🟢" if tipo == "Entrada" else "🔴"
    
    await query.edit_message_text(
        render_message("ag_prompt_primeira_data", emoji=emoji_tipo, descricao=dados['descricao'], valor=dados['valor'], categoria=categoria_nome),
        parse_mode='HTML'
    )
    
    return ASK_PRIMEIRO_EVENTO

async def ask_primeiro_evento(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Processa primeira data e vai para frequência"""
    try:
        data_primeiro = datetime.strptime(update.message.text, '%d/%m/%Y').date()
        if data_primeiro < datetime.now().date():
            await update.message.reply_text(render_message("ag_data_invalida"), parse_mode='HTML')
            return ASK_PRIMEIRO_EVENTO
            
        context.user_data['novo_agendamento']['data_primeiro_evento'] = data_primeiro
        
        # Resumo e pergunta da frequência
        dados = context.user_data['novo_agendamento']
        tipo = dados['tipo']
        emoji_tipo = "🟢" if tipo == "Entrada" else "🔴"
        data_formatada = data_primeiro.strftime('%d/%m/%Y')
        
        keyboard = [
            [InlineKeyboardButton("� Mensalmente", callback_data="ag_freq_mensal")],
            [InlineKeyboardButton("� Semanalmente", callback_data="ag_freq_semanal")],
            [InlineKeyboardButton("� Apenas uma vez", callback_data="ag_freq_unico")],
        ]
        
        await update.message.reply_text(
            render_message("ag_prompt_frequencia", emoji=emoji_tipo, descricao=dados['descricao'], valor=dados['valor'], data=data_formatada),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
        
        return ASK_FREQUENCIA
        
    except ValueError:
        await update.message.reply_text(
            "⚠️ <b>Formato inválido</b>\n\n"
            "Use o formato <code>DD/MM/AAAA</code>\n\n"
            "💡 <i>Exemplo:</i> <code>25/01/2025</code>",
            parse_mode='HTML'
        )
        return ASK_PRIMEIRO_EVENTO

async def ask_frequencia(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Processa frequência e define próximo passo"""
    query = update.callback_query
    await query.answer()
    
    frequencia = query.data.split('_')[-1]
    context.user_data['novo_agendamento']['frequencia'] = frequencia

    if frequencia == 'unico':
        context.user_data['novo_agendamento']['total_parcelas'] = 1
        return await show_agendamento_confirmation(update, context)

    # Traduz frequência para texto amigável
    freq_texto = {
        'mensal': 'Mensalmente',
        'semanal': 'Semanalmente'
    }.get(frequencia, frequencia)

    keyboard = [
        [InlineKeyboardButton("🔢 Número fixo de vezes", callback_data="ag_rec_fixo")],
        [InlineKeyboardButton("♾️ Contínuo (sem fim)", callback_data="ag_rec_continuo")],
    ]
    
    await query.edit_message_text(
        render_message("ag_prompt_recorrencia", freq=freq_texto),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )
    return ASK_TIPO_RECORRENCIA

async def ask_tipo_recorrencia(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Processa tipo de recorrência"""
    query = update.callback_query
    await query.answer()
    tipo_recorrencia = query.data.split('_')[-1]

    if tipo_recorrencia == 'continuo':
        context.user_data['novo_agendamento']['total_parcelas'] = None
        return await show_agendamento_confirmation(update, context)
    
    await query.edit_message_text(render_message("ag_prompt_total_parcelas"), parse_mode='HTML')
    return ASK_TOTAL_PARCELAS

async def ask_total_parcelas(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Processa o número total de parcelas informado pelo usuário."""
    text = (update.message.text or "").strip()
    try:
        total_parcelas = int(text)
        if total_parcelas <= 0:
            raise ValueError("precisa ser positivo")
    except Exception:
        await update.message.reply_text(
            render_message("ag_total_parcelas_invalido"),
            parse_mode='HTML'
        )
        return ASK_TOTAL_PARCELAS

    context.user_data['novo_agendamento']['total_parcelas'] = total_parcelas
    return await show_agendamento_confirmation(update, context)

async def show_agendamento_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Tela de confirmação moderna"""
    data = context.user_data['novo_agendamento']
    
    # Emojis e formatação
    tipo_emoji = "🟢" if data['tipo'] == "Entrada" else "🔴"
    
    # Frequência em texto amigável
    freq_map = {
        'mensal': 'Mensalmente',
        'semanal': 'Semanalmente',
        'unico': 'Apenas uma vez'
    }
    freq_str = freq_map.get(data['frequencia'], data['frequencia'])
    
    # Informações de parcelas/recorrência
    if data.get('total_parcelas') == 1:
        recorrencia_str = "Evento único"
    elif data.get('total_parcelas') and data['total_parcelas'] > 1:
        recorrencia_str = f"{freq_str}, em {data['total_parcelas']}x"
    else:
        recorrencia_str = f"{freq_str}, contínuo"

    # Buscar categoria se houver
    categoria_nome = "Sem categoria"
    if data.get('id_categoria'):
        db = next(get_db())
        try:
            categoria = db.query(Categoria).filter(Categoria.id == data['id_categoria']).first()
            if categoria:
                categoria_nome = categoria.nome
        finally:
            db.close()

    # Resumo elegante
    summary = render_message(
        "ag_confirmacao_resumo",
        emoji=tipo_emoji,
        descricao=data['descricao'],
        valor=data['valor'],
        categoria=categoria_nome,
        data_primeira=data['data_primeiro_evento'].strftime('%d/%m/%Y'),
        recorrencia=recorrencia_str
    )
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Salvar", callback_data="ag_confirm_save"),
            InlineKeyboardButton("❌ Cancelar", callback_data="ag_confirm_cancel")
        ]
    ]
    
    # Determina como enviar a mensagem
    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.edit_message_text(
            summary, 
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
    elif hasattr(update, 'message'):
        await update.message.reply_text(
            summary, 
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
        
    return CONFIRM_AGENDAMENTO

async def save_agendamento(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Salva agendamento com feedback elegante"""
    query = update.callback_query
    await query.answer()
    
    # Mostra mensagem de salvamento
    await query.edit_message_text(render_message("ag_salvando"), parse_mode='HTML')

    db = next(get_db())
    try:
        user_info = query.from_user
        usuario_db = get_or_create_user(db, user_info.id, user_info.full_name)
        data = context.user_data['novo_agendamento']

        novo_agendamento = Agendamento(
            id_usuario=usuario_db.id,
            descricao=data['descricao'],
            valor=data['valor'],
            tipo=data['tipo'],
            id_categoria=data.get('id_categoria'),
            data_primeiro_evento=data['data_primeiro_evento'],
            proxima_data_execucao=data['data_primeiro_evento'],
            frequencia=data['frequencia'],
            total_parcelas=data.get('total_parcelas'),
            parcela_atual=0,
            ativo=True
        )
        db.add(novo_agendamento)
        db.commit()
        
        # Feedback de sucesso elegante
        tipo_emoji = "🟢" if data['tipo'] == "Entrada" else "🔴"
        freq_map = {
            'mensal': 'Mensalmente',
            'semanal': 'Semanalmente', 
            'unico': 'Uma vez'
        }
        freq_str = freq_map.get(data['frequencia'], data['frequencia'])
        
        await query.edit_message_text(
            render_message(
                "ag_criado_sucesso",
                emoji=tipo_emoji,
                descricao=data['descricao'],
                valor=data['valor'],
                frequencia=freq_str,
                data_proxima=data['data_primeiro_evento'].strftime('%d/%m/%Y')
            ),
            parse_mode='HTML'
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao salvar agendamento: {e}", exc_info=True)
        await query.edit_message_text(render_message("ag_erro_salvar", tone="error"), parse_mode='HTML')
    finally:
        db.close()
        context.user_data.clear()
        
    return ConversationHandler.END

async def listar_agendamentos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    
    db = next(get_db())
    usuario_db = get_or_create_user(db, user_id, "")
    agendamentos = db.query(Agendamento).filter(Agendamento.id_usuario == usuario_db.id, Agendamento.ativo == True).order_by(Agendamento.proxima_data_execucao.asc()).all()
    db.close()

    if not agendamentos:
        await query.edit_message_text(render_message("ag_lista_vazia"))
        return

    await query.edit_message_text(render_message("ag_lista_header"), parse_mode='HTML')
    for ag in agendamentos:
        tipo_emoji = '🟢' if ag.tipo == 'Entrada' else '🔴'
        
        if ag.total_parcelas:
            status_str = f"Parcela {ag.parcela_atual + 1} de {ag.total_parcelas}"
        else:
            status_str = "Contínuo"

        mensagem = (
            f"--- \n"
            f"{tipo_emoji} <b>{ag.descricao}</b>\n"
            f"💰 Valor: R$ {ag.valor:.2f}\n"
            f"🗓️ Próximo: {ag.proxima_data_execucao.strftime('%d/%m/%Y')}\n"
            f"🔄 Status: {status_str}"
        )
        keyboard = [[InlineKeyboardButton("🗑️ Cancelar Agendamento", callback_data=f"ag_cancelar_{ag.id}")]]
        await context.bot.send_message(chat_id=user_id, text=mensagem, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))

async def cancelar_agendamento_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancela um agendamento existente"""
    query = update.callback_query
    await query.answer()
    agendamento_id = int(query.data.split('_')[-1])
    user_id = query.from_user.id

    db = next(get_db())
    try:
        ag_para_cancelar = db.query(Agendamento).join(Usuario).filter(
            Agendamento.id == agendamento_id,
            Usuario.telegram_id == user_id
        ).first()

        if ag_para_cancelar:
            ag_para_cancelar.ativo = False
            db.commit()
            await query.edit_message_text(
                render_message("ag_cancelar_sucesso", descricao=ag_para_cancelar.descricao),
                reply_markup=None,
                parse_mode='HTML'
            )
        else:
            await query.edit_message_text(
                render_message("ag_nao_encontrado", tone="error"),
                reply_markup=None,
                parse_mode='HTML'
            )
    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao cancelar agendamento {agendamento_id}: {e}", exc_info=True)
        await query.edit_message_text(
            render_message("ag_cancelar_erro", tone="error"),
            reply_markup=None,
            parse_mode='HTML'
        )
    finally:
        db.close()

async def handle_agendamento_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Processa ações do teclado de confirmação (salvar ou cancelar)."""
    query = update.callback_query
    await query.answer()

    data = query.data
    if data == "ag_confirm_save":
        return await save_agendamento(update, context)
    if data == "ag_confirm_cancel":
        await query.edit_message_text(render_message("ag_cancelado"), parse_mode='HTML')
        context.user_data.clear()
        return ConversationHandler.END

    # Qualquer outra ação apenas encerra silenciosamente
    return ConversationHandler.END


agendamento_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(agendamento_menu_callback, pattern='^agendamento_novo$')],
    states={
        ASK_TIPO: [CallbackQueryHandler(ask_tipo, pattern='^ag_tipo_')],
        ASK_DESCRICAO_AGENDAMENTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_descricao)],
        ASK_VALOR_AGENDAMENTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_valor)],
        ASK_CATEGORIA_AGENDAMENTO: [CallbackQueryHandler(ask_categoria, pattern='^ag_cat_')],
        ASK_PRIMEIRO_EVENTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_primeiro_evento)],
        ASK_FREQUENCIA: [CallbackQueryHandler(ask_frequencia, pattern='^ag_freq_')],
        ASK_TIPO_RECORRENCIA: [CallbackQueryHandler(ask_tipo_recorrencia, pattern='^ag_rec_')],
        ASK_TOTAL_PARCELAS: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_total_parcelas)],
        CONFIRM_AGENDAMENTO: [
            CallbackQueryHandler(handle_agendamento_confirmation, pattern='^ag_confirm_')
        ]
    },
    fallbacks=[CommandHandler('cancelar', cancel)],
    per_message=False,
    per_user=True,
    per_chat=True
)

