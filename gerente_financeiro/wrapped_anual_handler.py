"""
Handler para comando /meu_wrapped - Teste do Wrapped Anual
"""
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from database.database import get_db, get_or_create_user
from .wrapped_anual import enviar_wrapped_manual

logger = logging.getLogger(__name__)


async def comando_meu_wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Comando /meu_wrapped [ano] - Gera wrapped financeiro de um ano específico
    Se não especificar ano, usa o ano atual
    
    Exemplos:
    /meu_wrapped          -> Wrapped do ano atual
    /meu_wrapped 2024     -> Wrapped de 2024
    """
    user = update.effective_user
    
    # Verificar se foi passado o ano
    ano = datetime.now().year
    if context.args:
        try:
            ano = int(context.args[0])
            if ano < 2020 or ano > datetime.now().year:
                await update.message.reply_text(
                    f"❌ Ano inválido! Use um ano entre 2020 e {datetime.now().year}."
                )
                return
        except ValueError:
            await update.message.reply_text(
                "❌ Formato inválido! Use: /meu_wrapped 2024"
            )
            return
    
    await update.message.reply_text(
        f"🎊 Gerando seu Wrapped Financeiro de {ano}...\n"
        f"Isso pode levar alguns segundos! ⏳"
    )
    
    db = next(get_db())
    try:
        usuario_db = get_or_create_user(db, user.id, user.full_name)
        
        # Verificar se tem dados do ano solicitado
        from models import Lancamento
        from sqlalchemy import and_, extract, func
        
        tem_dados = db.query(func.count(Lancamento.id)).filter(
            and_(
                Lancamento.id_usuario == usuario_db.id,
                extract('year', Lancamento.data_transacao) == ano
            )
        ).scalar() > 0
        
        if not tem_dados:
            await update.message.reply_html(
                f"📊 <b>Sem dados para {ano}</b>\n\n"
                f"Você ainda não tem transações registradas em {ano}.\n\n"
                f"💡 <i>O Wrapped será enviado automaticamente no dia 31 de dezembro!</i>"
            )
            return
        
        # Gerar e enviar wrapped
        sucesso = await enviar_wrapped_manual(context.bot, usuario_db, ano)
        
        if sucesso:
            logger.info(f"✅ Wrapped de {ano} enviado para {user.full_name}")
        else:
            await update.message.reply_text(
                "❌ Ops! Ocorreu um erro ao gerar seu wrapped. "
                "Tente novamente mais tarde."
            )
        
    except Exception as e:
        logger.error(f"❌ Erro no comando meu_wrapped: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ Ops! Ocorreu um erro ao processar seu pedido. "
            "Tente novamente mais tarde."
        )
    finally:
        db.close()


# Handler para registrar no bot
meu_wrapped_handler = CommandHandler('meu_wrapped', comando_meu_wrapped)
