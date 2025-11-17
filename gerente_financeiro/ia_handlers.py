"""
🤖 Handlers para Análises Inteligentes com IA
==============================================

Comandos do bot que usam IA para análises avançadas de gastos.

Autor: Henrique Freitas
Data: 17/11/2025
"""

import logging
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from sqlalchemy import and_, extract
from database.database import get_db, get_or_create_user
from models import Lancamento, Usuario
from .analises_ia import get_analisador

logger = logging.getLogger(__name__)


async def comando_insights(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Comando /insights - Análise inteligente dos gastos do mês
    """
    user = update.effective_user
    await update.message.reply_text("🤖 Analisando seus gastos com IA... Aguarde um momento.")
    
    db = next(get_db())
    try:
        usuario_db = get_or_create_user(db, user.id, user.full_name)
        
        # Buscar transações do mês atual
        hoje = datetime.now()
        transacoes = db.query(Lancamento).filter(
            and_(
                Lancamento.id_usuario == usuario_db.id,
                Lancamento.tipo == 'Saída',
                extract('year', Lancamento.data_transacao) == hoje.year,
                extract('month', Lancamento.data_transacao) == hoje.month
            )
        ).all()
        
        if not transacoes:
            await update.message.reply_html(
                "📊 <b>Sem dados para análise</b>\n\n"
                "Você ainda não tem gastos registrados este mês.\n"
                "Use /lancamento para adicionar transações!"
            )
            return
        
        # Converter para formato dict
        transacoes_dict = [
            {
                'data': t.data_transacao.strftime('%d/%m/%Y'),
                'descricao': t.descricao,
                'valor': float(t.valor),
                'categoria': t.categoria.nome if t.categoria else 'Outros'
            }
            for t in transacoes
        ]
        
        # Gerar análise com IA
        analisador = get_analisador()
        analise = analisador.analisar_padrao_gastos(transacoes_dict, periodo_dias=30)
        
        await update.message.reply_html(
            f"🤖 <b>Análise Inteligente - {hoje.strftime('%B/%Y')}</b>\n\n"
            f"{analise}\n\n"
            f"💡 <i>Use /economia para receber sugestões personalizadas!</i>"
        )
        
    except Exception as e:
        logger.error(f"❌ Erro no comando insights: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ Ops! Ocorreu um erro ao gerar a análise. Tente novamente mais tarde."
        )
    finally:
        db.close()


async def comando_economia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Comando /economia [valor] - Sugestões de como economizar
    Exemplo: /economia 500
    """
    user = update.effective_user
    
    # Verificar se foi passado o valor meta
    meta_economia = 300.0  # Valor padrão
    if context.args:
        try:
            meta_economia = float(context.args[0].replace(',', '.'))
        except ValueError:
            await update.message.reply_text(
                "❌ Valor inválido! Use: /economia 500 (para economizar R$ 500)"
            )
            return
    
    await update.message.reply_text(
        f"💡 Gerando sugestões para economizar R$ {meta_economia:.2f}..."
    )
    
    db = next(get_db())
    try:
        usuario_db = get_or_create_user(db, user.id, user.full_name)
        
        # Buscar transações dos últimos 30 dias
        hoje = datetime.now()
        data_inicio = hoje - timedelta(days=30)
        
        transacoes = db.query(Lancamento).filter(
            and_(
                Lancamento.id_usuario == usuario_db.id,
                Lancamento.tipo == 'Saída',
                Lancamento.data_transacao >= data_inicio
            )
        ).all()
        
        if not transacoes:
            await update.message.reply_html(
                "📊 <b>Sem dados para análise</b>\n\n"
                "Você ainda não tem gastos registrados.\n"
                "Use /lancamento para adicionar transações!"
            )
            return
        
        # Converter para formato dict
        transacoes_dict = [
            {
                'data': t.data_transacao.strftime('%d/%m/%Y'),
                'descricao': t.descricao,
                'valor': float(t.valor),
                'categoria': t.categoria.nome if t.categoria else 'Outros'
            }
            for t in transacoes
        ]
        
        # Gerar sugestões com IA
        analisador = get_analisador()
        sugestoes = analisador.sugerir_economia(transacoes_dict, meta_economia)
        
        await update.message.reply_html(
            f"💡 <b>Sugestões Personalizadas de Economia</b>\n"
            f"🎯 Meta: R$ {meta_economia:.2f}/mês\n\n"
            f"{sugestoes}\n\n"
            f"💪 <i>Pequenas mudanças fazem grande diferença!</i>"
        )
        
    except Exception as e:
        logger.error(f"❌ Erro no comando economia: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ Ops! Ocorreu um erro ao gerar sugestões. Tente novamente mais tarde."
        )
    finally:
        db.close()


async def comando_comparar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Comando /comparar - Compara gastos do mês atual com o anterior
    """
    user = update.effective_user
    await update.message.reply_text("📊 Comparando seus gastos com o mês anterior...")
    
    db = next(get_db())
    try:
        usuario_db = get_or_create_user(db, user.id, user.full_name)
        
        hoje = datetime.now()
        
        # Mês atual
        transacoes_atual = db.query(Lancamento).filter(
            and_(
                Lancamento.id_usuario == usuario_db.id,
                Lancamento.tipo == 'Saída',
                extract('year', Lancamento.data_transacao) == hoje.year,
                extract('month', Lancamento.data_transacao) == hoje.month
            )
        ).all()
        
        # Mês anterior
        mes_anterior = hoje.replace(day=1) - timedelta(days=1)
        transacoes_anterior = db.query(Lancamento).filter(
            and_(
                Lancamento.id_usuario == usuario_db.id,
                Lancamento.tipo == 'Saída',
                extract('year', Lancamento.data_transacao) == mes_anterior.year,
                extract('month', Lancamento.data_transacao) == mes_anterior.month
            )
        ).all()
        
        if not transacoes_atual and not transacoes_anterior:
            await update.message.reply_html(
                "📊 <b>Sem dados para comparação</b>\n\n"
                "Você ainda não tem gastos registrados nos últimos 2 meses."
            )
            return
        
        # Converter para formato dict
        atual_dict = [
            {
                'data': t.data_transacao.strftime('%d/%m/%Y'),
                'descricao': t.descricao,
                'valor': float(t.valor),
                'categoria': t.categoria.nome if t.categoria else 'Outros'
            }
            for t in transacoes_atual
        ]
        
        anterior_dict = [
            {
                'data': t.data_transacao.strftime('%d/%m/%Y'),
                'descricao': t.descricao,
                'valor': float(t.valor),
                'categoria': t.categoria.nome if t.categoria else 'Outros'
            }
            for t in transacoes_anterior
        ]
        
        # Gerar comparação com IA
        analisador = get_analisador()
        comparacao = analisador.comparar_periodos(atual_dict, anterior_dict)
        
        mes_atual_nome = hoje.strftime('%B')
        mes_anterior_nome = mes_anterior.strftime('%B')
        
        await update.message.reply_html(
            f"📊 <b>Comparação de Gastos</b>\n"
            f"📅 {mes_anterior_nome} vs {mes_atual_nome}\n\n"
            f"{comparacao}\n\n"
            f"💡 <i>Use /insights para análise detalhada do mês atual!</i>"
        )
        
    except Exception as e:
        logger.error(f"❌ Erro no comando comparar: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ Ops! Ocorreu um erro ao comparar períodos. Tente novamente mais tarde."
        )
    finally:
        db.close()


async def comando_alertas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Comando /alertas - Detecta gastos anormais ou suspeitos
    """
    user = update.effective_user
    await update.message.reply_text("🔍 Analisando padrões e procurando anomalias...")
    
    db = next(get_db())
    try:
        usuario_db = get_or_create_user(db, user.id, user.full_name)
        
        hoje = datetime.now()
        
        # Transações dos últimos 30 dias (recentes)
        data_inicio_recente = hoje - timedelta(days=30)
        transacoes_recentes = db.query(Lancamento).filter(
            and_(
                Lancamento.id_usuario == usuario_db.id,
                Lancamento.tipo == 'Saída',
                Lancamento.data_transacao >= data_inicio_recente
            )
        ).all()
        
        # Histórico dos últimos 6 meses (para comparação)
        data_inicio_historico = hoje - timedelta(days=180)
        historico = db.query(Lancamento).filter(
            and_(
                Lancamento.id_usuario == usuario_db.id,
                Lancamento.tipo == 'Saída',
                Lancamento.data_transacao >= data_inicio_historico,
                Lancamento.data_transacao < data_inicio_recente
            )
        ).all()
        
        if not transacoes_recentes:
            await update.message.reply_html(
                "📊 <b>Sem dados recentes</b>\n\n"
                "Você não tem gastos registrados nos últimos 30 dias."
            )
            return
        
        if not historico:
            await update.message.reply_html(
                "📊 <b>Sem histórico para comparação</b>\n\n"
                "Preciso de pelo menos 2 meses de dados para detectar anomalias.\n"
                "Continue usando o bot e em breve terei insights para você!"
            )
            return
        
        # Converter para formato dict
        recentes_dict = [
            {
                'data': t.data_transacao.strftime('%d/%m/%Y'),
                'descricao': t.descricao,
                'valor': float(t.valor),
                'categoria': t.categoria.nome if t.categoria else 'Outros'
            }
            for t in transacoes_recentes
        ]
        
        historico_dict = [
            {
                'data': t.data_transacao.strftime('%d/%m/%Y'),
                'descricao': t.descricao,
                'valor': float(t.valor),
                'categoria': t.categoria.nome if t.categoria else 'Outros'
            }
            for t in historico
        ]
        
        # Detectar anomalias
        analisador = get_analisador()
        anomalias = analisador.detectar_anomalias(recentes_dict, historico_dict)
        
        if not anomalias:
            await update.message.reply_html(
                "✅ <b>Tudo Normal!</b>\n\n"
                "Não detectei nenhum gasto anormal nos últimos 30 dias.\n"
                "Seus gastos estão dentro do padrão esperado. 👍"
            )
        else:
            texto_alertas = "🚨 <b>Alertas Detectados</b>\n\n"
            texto_alertas += f"Encontrei <b>{len(anomalias)}</b> gasto(s) fora do padrão:\n\n"
            
            for idx, anomalia in enumerate(anomalias[:5], 1):  # Máximo 5 alertas
                t = anomalia['transacao']
                motivo = anomalia['motivo']
                severidade = anomalia['severidade']
                
                emoji = "🔴" if severidade == 'alta' else "🟡"
                
                texto_alertas += (
                    f"{emoji} <b>{idx}. {t['descricao']}</b>\n"
                    f"   Valor: R$ {t['valor']:.2f}\n"
                    f"   {motivo}\n\n"
                )
            
            if len(anomalias) > 5:
                texto_alertas += f"... e mais {len(anomalias) - 5} alertas.\n\n"
            
            texto_alertas += "💡 <i>Verifique se estes gastos estão corretos!</i>"
            
            await update.message.reply_html(texto_alertas)
        
    except Exception as e:
        logger.error(f"❌ Erro no comando alertas: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ Ops! Ocorreu um erro ao analisar alertas. Tente novamente mais tarde."
        )
    finally:
        db.close()


# Handlers para registrar no bot
insights_handler = CommandHandler('insights', comando_insights)
economia_handler = CommandHandler('economia', comando_economia)
comparar_handler = CommandHandler('comparar', comando_comparar)
alertas_handler = CommandHandler('alertas', comando_alertas)
