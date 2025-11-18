"""
Handler para testar o Assistente Proativo manualmente
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from database.database import get_db, get_or_create_user
from .assistente_proativo import analisar_e_notificar_usuario

logger = logging.getLogger(__name__)


async def comando_teste_assistente(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Comando /teste_assistente - Executa análise proativa manualmente
    (Útil para testes e debugging)
    """
    user = update.effective_user
    await update.message.reply_text("🤖 Analisando seus dados... Aguarde um momento.")
    
    db = next(get_db())
    try:
        usuario_db = get_or_create_user(db, user.id, user.full_name)
        
        # Executar análise completa
        alertas_enviados = await analisar_e_notificar_usuario(context.bot, usuario_db)
        
        if not alertas_enviados:
            await update.message.reply_html(
                "✅ <b>Tudo certo!</b>\n\n"
                "Não detectei nenhum alerta para você no momento.\n"
                "Continue assim! 👏\n\n"
                "<i>O assistente proativo analisa automaticamente "
                "seus dados todos os dias às 20h.</i>"
            )
        else:
            await update.message.reply_html(
                "📨 <b>Alertas enviados!</b>\n\n"
                "Verifique as mensagens acima com as análises detectadas.\n\n"
                "<i>Este recurso roda automaticamente todo dia às 20h.</i>"
            )
        
    except Exception as e:
        logger.error(f"❌ Erro no comando teste_assistente: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ Ops! Ocorreu um erro ao executar a análise. "
            "Tente novamente mais tarde."
        )
    finally:
        db.close()


# Handler para registrar no bot
teste_assistente_handler = CommandHandler('teste_assistente', comando_teste_assistente)
