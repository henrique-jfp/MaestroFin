# gerente_financeiro/relatorio_handler.py

import logging
from datetime import datetime
from io import BytesIO
from dateutil.relativedelta import relativedelta
from telegram import Update, InputFile
from telegram.ext import ContextTypes, CommandHandler

# Importar gerador PDF
try:
    from .pdf_generator import generate_financial_pdf
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    print("❌ Erro: pdf_generator não encontrado ou com erro de importação.")

from database.database import get_db
from .services import gerar_contexto_relatorio

logger = logging.getLogger(__name__)

async def gerar_relatorio_comando(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Gera e envia o Relatório Financeiro Premium em PDF.
    """
    user = update.effective_user
    hoje = datetime.now()
    
    # Determina período (Mês atual ou anterior)
    if context.args and context.args[0].lower() in ['passado', 'anterior']:
        data_alvo = hoje - relativedelta(months=1)
        periodo_str = f"do mês passado ({data_alvo.strftime('%B/%Y')})"
    else:
        data_alvo = hoje
        periodo_str = "deste mês"
        
    mes_alvo = data_alvo.month
    ano_alvo = data_alvo.year

    # Mensagem de feedback inicial
    msg = await update.message.reply_text(f"🏦 Gerando relatório Private {periodo_str}...\nAguarde um momento.")
    
    db = next(get_db())
    user_id = user.id
    
    try:
        # 1. Busca dados brutos do serviço
        contexto_dados = gerar_contexto_relatorio(db, user_id, mes_alvo, ano_alvo)
        
        # Verifica se existem dados
        if not contexto_dados or not contexto_dados.get("has_data", False):
            await msg.edit_text(f"📉 Não encontrei dados suficientes em {periodo_str} para gerar um relatório completo.")
            return

        # 2. Prepara o contexto limpo para o PDF Generator
        # Isso garante que os dados cheguem no formato correto que o pdf_generator espera
        
        pdf_context = {
            'usuario_nome': user.full_name or "Investidor",
            'periodo_extenso': data_alvo.strftime('%B de %Y').capitalize(),
            'receita_total': float(contexto_dados.get('receita_total', 0.0)),
            'despesa_total': float(contexto_dados.get('despesa_total', 0.0)),
            'saldo_mes': float(contexto_dados.get('saldo_mes', 0.0)),
            'taxa_poupanca': float(contexto_dados.get('taxa_poupanca', 0.0)),
            'insights': contexto_dados.get('insights', []),
            # Passa a lista de tuplas (Categoria, Valor)
            'gastos_agrupados': contexto_dados.get('gastos_agrupados', []),
            # Passa a lista de dicts também, caso o gerador precise de fallback
            'gastos_por_categoria': contexto_dados.get('gastos_por_categoria_dict', [])
        }
        
        logger.info(f"Gerando PDF para {pdf_context['usuario_nome']} com {len(pdf_context['gastos_agrupados'])} categorias.")

        # 3. Gera o PDF
        if PDF_AVAILABLE:
            pdf_bytes = generate_financial_pdf(pdf_context)
            
            filename = f"Relatorio_MaestroFin_{data_alvo.strftime('%m_%Y')}.pdf"
            
            # Envia o arquivo
            await update.message.reply_document(
                document=InputFile(BytesIO(pdf_bytes), filename=filename),
                caption=(
                    f"💎 <b>Relatório Financeiro Private</b>\n"
                    f"📅 {pdf_context['periodo_extenso']}\n\n"
                    f"💰 Saldo: R$ {pdf_context['saldo_mes']:,.2f}\n"
                    f"📊 Poupança: {pdf_context['taxa_poupanca']:.1f}%"
                ),
                parse_mode='HTML'
            )
            # Apaga a mensagem de "carregando"
            await msg.delete()
        else:
            await msg.edit_text("❌ Erro interno: Módulo de geração de PDF não está disponível.")

    except Exception as e:
        logger.error(f"Erro crítico ao gerar relatório: {e}", exc_info=True)
        await msg.edit_text("❌ Ocorreu um erro ao processar seu relatório. Tente novamente mais tarde.")
    finally:
        db.close()

relatorio_handler = CommandHandler('relatorio', gerar_relatorio_comando)