# gerente_financeiro/gamification_handler.py
import logging
from sqlalchemy.orm import Session
from telegram import Update
from telegram.ext import ContextTypes
from database.database import get_db
from models import Usuario
from .gamification_service import LEVELS

logger = logging.getLogger(__name__)

async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Exibe o perfil de gamificação do usuário."""
    user_id = update.effective_user.id
    db: Session = next(get_db())
    try:
        usuario = db.query(Usuario).filter(Usuario.telegram_id == user_id).first()
        if not usuario:
            await update.message.reply_text("Usuário não encontrado. Use /start para começar.")
            return

        level_info = LEVELS.get(usuario.level, {})
        next_level_info = LEVELS.get(usuario.level + 1)
        
        xp_necessario_str = ""
        if next_level_info:
            xp_faltante = next_level_info["xp_necessario"] - usuario.xp
            xp_necessario_str = f"({xp_faltante} XP para o Nível {usuario.level + 1})"

        mensagem = (
            f"🎮 **SEU PERFIL DE JOGO**\n\n"
            f"👤 @{update.effective_user.username or usuario.nome_completo}\n"
            f"🏆 **Nível {usuario.level} - {level_info.get('titulo', 'N/A')}**\n"
            f"⭐ {usuario.xp} XP {xp_necessario_str}\n"
            f"🔥 Sequência: {usuario.streak_dias} dias\n"
            # f"💰 Pontos Economia: (em breve)\n"
            # f"📊 Ranking: (em breve)\n\n"
            # f"🏅 **CONQUISTAS RECENTES:**\n"
            # f"• (em breve)"
        )
        
        await update.message.reply_html(mensagem)

    finally:
        db.close()

async def show_rankings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Exibe os rankings globais."""
    user_id = update.effective_user.id
    db: Session = next(get_db())
    try:
        # Ranking de XP Global
        top_10_xp = db.query(Usuario).order_by(Usuario.xp.desc()).limit(10).all()
        
        ranking_xp_str = "🏆 **RANKING GLOBAL DE XP**\n\n"
        for i, u in enumerate(top_10_xp):
            level_info = LEVELS.get(u.level, {})
            emoji = ["🥇", "🥈", "🥉"][i] if i < 3 else f"{i+1}."
            nome = u.nome_completo.split(' ')[0] if u.nome_completo else f"Usuário {u.id}"
            ranking_xp_str += f"{emoji} {nome} - Nível {u.level} ({u.xp} XP)\n"

        # Posição do usuário atual
        # Esta query pode ser lenta em bancos grandes, mas para começar é suficiente
        todos_usuarios = db.query(Usuario.telegram_id).order_by(Usuario.xp.desc()).all()
        try:
            posicao = [u.telegram_id for u in todos_usuarios].index(user_id) + 1
            usuario_atual = db.query(Usuario).filter(Usuario.telegram_id == user_id).first()
            ranking_xp_str += f"\n...\n🔹 **Sua Posição: #{posicao}** - Nível {usuario_atual.level} ({usuario_atual.xp} XP)"
        except ValueError:
            ranking_xp_str += "\n\n🔹 Sua posição aparecerá aqui assim que você ganhar XP."

        ranking_xp_str += "\n\n---\n\n💵 **RANKING DE ECONOMIA SEMANAL**\n"
        ranking_xp_str += "Em breve! Continue economizando para se preparar."

        await update.message.reply_html(ranking_xp_str)

    finally:
        db.close()