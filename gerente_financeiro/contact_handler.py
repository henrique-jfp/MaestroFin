# gerente_financeiro/relatorio_handler.py

import logging
from datetime import datetime
from io import BytesIO
import os
from dateutil.relativedelta import relativedelta

from telegram import Update, InputFile
from telegram.ext import ContextTypes, CommandHandler

# Importa o novo gerador PDF
try:
    from .pdf_generator import generate_financial_pdf
    PDF_AVAILABLE = True
except ImportError as e:
    print(f"❌ Erro ao importar gerador PDF: {e}")
    PDF_AVAILABLE = False

from database.database import get_db
from .services import gerar_contexto_relatorio

logger = logging.getLogger(__name__)

async def gerar_relatorio_comando(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gera e envia o Relatório Financeiro Premium."""
    
    user = update.effective_user
    hoje = datetime.now()
    
    # Lógica de período (Mês atual ou passado)
    if context.args and context.args[0].lower() in ['passado', 'anterior']:
        data_alvo = hoje - relativedelta(months=1)
        periodo_str = f"do mês passado ({data_alvo.strftime('%B/%Y')})"
    else:
        data_alvo = hoje
        periodo_str = "deste mês"
        
    mes_alvo = data_alvo.month
    ano_alvo = data_alvo.year

    msg_loading = await update.message.reply_text(f"🏦 Gerando seu relatório Private {periodo_str}...\nIsso pode levar alguns segundos.")
    
    db = next(get_db())
    user_id = user.id
    
    try:
        # Busca dados brutos do serviço existente
        contexto_dados = gerar_contexto_relatorio(db, user_id, mes_alvo, ano_alvo)
        
        if not contexto_dados or not contexto_dados.get("has_data"):
            await msg_loading.edit_text(f"📉 Não encontrei dados suficientes em {periodo_str} para gerar um relatório completo.")
            return

        # Enriquecer contexto para o PDF Generator
        # Adicionamos campos específicos para o visual premium
        contexto_dados['usuario_nome'] = user.full_name or "Investidor"
        contexto_dados['periodo_extenso'] = f"{data_alvo.strftime('%B de %Y').capitalize()}"
        
        # Se o serviço não retornar top_transacoes, cria uma lista vazia ou busca do DB
        if 'top_transacoes' not in contexto_dados:
            # Fallback simples se o service não prover
            contexto_dados['top_transacoes'] = [] 

        # Geração do PDF
        if PDF_AVAILABLE:
            pdf_bytes = generate_financial_pdf(contexto_dados)
            
            filename = f"Relatorio_MaestroFin_{data_alvo.strftime('%m_%Y')}.pdf"
            
            await update.message.reply_document(
                document=InputFile(BytesIO(pdf_bytes), filename=filename),
                caption=(
                    f"💎 <b>Seu Relatório Financeiro está pronto.</b>\n\n"
                    f"📅 Período: {contexto_dados['periodo_extenso']}\n"
                    f"💰 Saldo: R$ {contexto_dados.get('saldo_mes', 0):.2f}\n"
                    f"📊 Taxa de Poupança: {contexto_dados.get('taxa_poupanca', 0):.1f}%"
                ),
                parse_mode='HTML'
            )
            await msg_loading.delete()
        else:
            await msg_loading.edit_text("❌ Erro interno: Módulo de PDF indisponível.")

    except Exception as e:
        logger.error(f"Erro ao gerar relatório: {e}", exc_info=True)
        await msg_loading.edit_text("❌ Ocorreu um erro ao processar seu relatório. Tente novamente mais tarde.")
    finally:
        db.close()

relatorio_handler = CommandHandler('relatorio', gerar_relatorio_comando)