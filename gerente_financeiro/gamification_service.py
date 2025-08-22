# gerente_financeiro/gamification_service.py
import logging
from datetime import date, timedelta
from sqlalchemy.orm import Session
from models import Usuario

logger = logging.getLogger(__name__)

# --- CONFIGURAÇÕES DE GAMIFICAÇÃO ---

XP_ACTIONS = {
    "LANCAMENTO_MANUAL": 10,
    "LANCAMENTO_OCR": 25,
    "PERGUNTA_IA": 15,
    "VISUALIZAR_GRAFICO": 20,
    "PRIMEIRA_INTERACAO_DIA": 25,
    "META_ATINGIDA": 300,
    "RELATORIO_GERADO": 150,
    "AGENDAMENTO_CRIADO": 100,
}

LEVELS = {
    1: {"xp_necessario": 0, "titulo": "Aprendiz"},
    2: {"xp_necessario": 500, "titulo": "Organizador"},
    3: {"xp_necessario": 1500, "titulo": "Economista"},
    4: {"xp_necessario": 3500, "titulo": "Investidor"},
    5: {"xp_necessario": 7000, "titulo": "Especialista"},
    6: {"xp_necessario": 12000, "titulo": "Guru"},
    7: {"xp_necessario": 20000, "titulo": "Maestro"},
}

STREAK_BONUS = {
    3: 100,
    7: 200,
    30: 500,
}

async def award_xp(db: Session, user_id: int, action: str, context) -> None:
    """
    Concede XP a um usuário, verifica level up e envia notificação.
    """
    xp_to_add = XP_ACTIONS.get(action, 0)
    if xp_to_add == 0:
        return

    usuario = db.query(Usuario).filter(Usuario.telegram_id == user_id).first()
    if not usuario:
        return

    usuario.xp += xp_to_add
    logger.info(f"Usuário {user_id} ganhou {xp_to_add} XP pela ação: {action}. Total agora: {usuario.xp}")

    # Verificar Level Up
    current_level_info = LEVELS.get(usuario.level)
    next_level_info = LEVELS.get(usuario.level + 1)

    if next_level_info and usuario.xp >= next_level_info["xp_necessario"]:
        usuario.level += 1
        db.commit() # Salva o XP e o novo nível
        
        mensagem_levelup = (
            f"🎉✨ **LEVEL UP!** ✨🎉\n\n"
            f"Parabéns! Você alcançou o **Nível {usuario.level}** e agora é um(a) **{next_level_info['titulo']}**!\n\n"
            f"Sua dedicação está transformando sua vida financeira. Continue assim! 🚀"
        )
        await context.bot.send_message(chat_id=user_id, text=mensagem_levelup, parse_mode='Markdown')
    else:
        db.commit() # Salva o novo XP

async def check_and_update_streak(db: Session, user_id: int, context) -> None:
    """
    Verifica e atualiza a sequência de logins diários do usuário.
    """
    usuario = db.query(Usuario).filter(Usuario.telegram_id == user_id).first()
    if not usuario:
        return

    hoje = date.today()
    ultimo_login = usuario.ultimo_login

    if ultimo_login == hoje: # Já fez login hoje
        return

    # Conceder XP pela primeira interação do dia
    await award_xp(db, user_id, "PRIMEIRA_INTERACAO_DIA", context)

    if ultimo_login == hoje - timedelta(days=1): # Continua a sequência
        usuario.streak_dias += 1
        bonus = STREAK_BONUS.get(usuario.streak_dias)
        if bonus:
            usuario.xp += bonus
            await context.bot.send_message(
                chat_id=user_id,
                text=f"🔥 **SEQUÊNCIA DE {usuario.streak_dias} DIAS!**\n\nVocê ganhou +{bonus} XP de bônus por sua consistência! Continue assim!",
                parse_mode='Markdown'
            )
    else: # Quebrou a sequência
        usuario.streak_dias = 1
    
    usuario.ultimo_login = hoje
    db.commit()