"""
🎊 Wrapped Financeiro Anual - MaestroFin
========================================

Sistema que gera uma retrospectiva emocionante do ano financeiro do usuário,
similar ao Spotify Wrapped, com estatísticas, curiosidades e mensagem inspiradora.

Enviado automaticamente no dia 31 de dezembro às 13h.

Autor: Henrique Freitas
Data: 18/11/2025
Versão: 3.2.0
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy import func, and_, extract, desc
from decimal import Decimal
import calendar

from database.database import get_db
from models import Usuario, Lancamento, Objetivo, Categoria, ConquistaUsuario

logger = logging.getLogger(__name__)


# ============================================================================
# CÁLCULOS DE ESTATÍSTICAS ANUAIS
# ============================================================================

def calcular_resumo_financeiro(usuario_id: int, ano: int) -> Dict:
    """Calcula resumo geral de receitas e despesas do ano"""
    db = next(get_db())
    try:
        # Receitas totais
        receitas = db.query(func.sum(Lancamento.valor)).filter(
            and_(
                Lancamento.id_usuario == usuario_id,
                Lancamento.tipo == 'Entrada',
                extract('year', Lancamento.data_transacao) == ano
            )
        ).scalar() or 0
        
        # Despesas totais
        despesas = db.query(func.sum(Lancamento.valor)).filter(
            and_(
                Lancamento.id_usuario == usuario_id,
                Lancamento.tipo == 'Saída',
                extract('year', Lancamento.data_transacao) == ano
            )
        ).scalar() or 0
        
        receitas = float(receitas)
        despesas = float(despesas)
        economia = receitas - despesas
        taxa_poupanca = (economia / receitas * 100) if receitas > 0 else 0
        
        return {
            'receitas_total': receitas,
            'despesas_total': despesas,
            'economia_total': economia,
            'taxa_poupanca': taxa_poupanca
        }
    finally:
        db.close()


def calcular_categorias_top(usuario_id: int, ano: int, limit: int = 5) -> List[Dict]:
    """Retorna as categorias com maiores gastos do ano"""
    db = next(get_db())
    try:
        categorias = db.query(
            Categoria.nome,
            func.sum(Lancamento.valor).label('total'),
            func.count(Lancamento.id).label('quantidade')
        ).join(
            Lancamento, Lancamento.id_categoria == Categoria.id
        ).filter(
            and_(
                Lancamento.id_usuario == usuario_id,
                Lancamento.tipo == 'Saída',
                extract('year', Lancamento.data_transacao) == ano
            )
        ).group_by(
            Categoria.nome
        ).order_by(
            desc('total')
        ).limit(limit).all()
        
        return [
            {
                'categoria': cat.nome,
                'total': float(cat.total),
                'quantidade': cat.quantidade
            }
            for cat in categorias
        ]
    finally:
        db.close()


def calcular_evolucao_mensal(usuario_id: int, ano: int) -> Dict:
    """Calcula receitas e despesas mês a mês"""
    db = next(get_db())
    try:
        meses_dados = {}
        
        for mes in range(1, 13):
            receitas = db.query(func.sum(Lancamento.valor)).filter(
                and_(
                    Lancamento.id_usuario == usuario_id,
                    Lancamento.tipo == 'Entrada',
                    extract('year', Lancamento.data_transacao) == ano,
                    extract('month', Lancamento.data_transacao) == mes
                )
            ).scalar() or 0
            
            despesas = db.query(func.sum(Lancamento.valor)).filter(
                and_(
                    Lancamento.id_usuario == usuario_id,
                    Lancamento.tipo == 'Saída',
                    extract('year', Lancamento.data_transacao) == ano,
                    extract('month', Lancamento.data_transacao) == mes
                )
            ).scalar() or 0
            
            mes_nome = calendar.month_name[mes]
            meses_dados[mes_nome] = {
                'receitas': float(receitas),
                'despesas': float(despesas),
                'saldo': float(receitas) - float(despesas)
            }
        
        return meses_dados
    finally:
        db.close()


def encontrar_melhor_mes(usuario_id: int, ano: int) -> Dict:
    """Encontra o mês com maior economia"""
    db = next(get_db())
    try:
        melhor_mes = None
        maior_economia = float('-inf')
        
        for mes in range(1, 13):
            receitas = db.query(func.sum(Lancamento.valor)).filter(
                and_(
                    Lancamento.id_usuario == usuario_id,
                    Lancamento.tipo == 'Entrada',
                    extract('year', Lancamento.data_transacao) == ano,
                    extract('month', Lancamento.data_transacao) == mes
                )
            ).scalar() or 0
            
            despesas = db.query(func.sum(Lancamento.valor)).filter(
                and_(
                    Lancamento.id_usuario == usuario_id,
                    Lancamento.tipo == 'Saída',
                    extract('year', Lancamento.data_transacao) == ano,
                    extract('month', Lancamento.data_transacao) == mes
                )
            ).scalar() or 0
            
            economia = float(receitas) - float(despesas)
            
            if economia > maior_economia:
                maior_economia = economia
                melhor_mes = calendar.month_name[mes]
        
        return {
            'nome': melhor_mes,
            'economia': maior_economia
        }
    finally:
        db.close()


def encontrar_maior_gasto(usuario_id: int, ano: int) -> Dict:
    """Encontra a transação de maior valor do ano"""
    db = next(get_db())
    try:
        maior = db.query(Lancamento).filter(
            and_(
                Lancamento.id_usuario == usuario_id,
                Lancamento.tipo == 'Saída',
                extract('year', Lancamento.data_transacao) == ano
            )
        ).order_by(desc(Lancamento.valor)).first()
        
        if maior:
            return {
                'descricao': maior.descricao,
                'valor': float(maior.valor),
                'data': maior.data_transacao.strftime('%d/%m/%Y'),
                'categoria': maior.categoria.nome if maior.categoria else 'Outros'
            }
        
        return None
    finally:
        db.close()


def calcular_metas_ano(usuario_id: int, ano: int) -> Dict:
    """Analisa metas criadas e atingidas no ano"""
    db = next(get_db())
    try:
        # Metas criadas no ano
        metas_criadas = db.query(Objetivo).filter(
            and_(
                Objetivo.id_usuario == usuario_id,
                extract('year', Objetivo.criado_em) == ano
            )
        ).all()
        
        # Metas atingidas (valor_atual >= valor_meta)
        metas_atingidas = [
            meta for meta in metas_criadas
            if meta.valor_atual >= meta.valor_meta
        ]
        
        return {
            'metas_totais': len(metas_criadas),
            'metas_atingidas': len(metas_atingidas),
            'taxa_sucesso': (len(metas_atingidas) / len(metas_criadas) * 100) if metas_criadas else 0,
            'metas_detalhes': [
                {
                    'descricao': meta.descricao,
                    'valor_meta': float(meta.valor_meta),
                    'valor_atual': float(meta.valor_atual),
                    'atingida': meta.valor_atual >= meta.valor_meta
                }
                for meta in metas_criadas
            ]
        }
    finally:
        db.close()


def calcular_estatisticas_uso(usuario_id: int, ano: int) -> Dict:
    """Calcula estatísticas de uso do bot no ano"""
    db = next(get_db())
    try:
        # Total de transações registradas
        total_lancamentos = db.query(func.count(Lancamento.id)).filter(
            and_(
                Lancamento.id_usuario == usuario_id,
                extract('year', Lancamento.data_transacao) == ano
            )
        ).scalar() or 0
        
        # Dias com atividade
        dias_ativos = db.query(
            func.count(func.distinct(func.date(Lancamento.data_transacao)))
        ).filter(
            and_(
                Lancamento.id_usuario == usuario_id,
                extract('year', Lancamento.data_transacao) == ano
            )
        ).scalar() or 0
        
        # Conquistas desbloqueadas no ano
        conquistas = db.query(func.count(ConquistaUsuario.id)).filter(
            and_(
                ConquistaUsuario.id_usuario == usuario_id,
                extract('year', ConquistaUsuario.data_conquista) == ano
            )
        ).scalar() or 0
        
        # XP total (se tiver campo de XP)
        usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
        xp_total = usuario.xp if hasattr(usuario, 'xp') else 0
        nivel_atual = usuario.nivel if hasattr(usuario, 'nivel') else 0
        
        return {
            'total_lancamentos': total_lancamentos,
            'dias_ativos': dias_ativos,
            'conquistas': conquistas,
            'xp_total': xp_total,
            'nivel_atual': nivel_atual
        }
    finally:
        db.close()


# ============================================================================
# GERAÇÃO DE CURIOSIDADES
# ============================================================================

def gerar_curiosidades(usuario_id: int, ano: int) -> List[str]:
    """Gera insights curiosos sobre os gastos do usuário"""
    db = next(get_db())
    curiosidades = []
    
    try:
        # Palavras-chave para buscar em descrições
        palavras_interesse = {
            'pizza': '🍕 pizza',
            'café': '☕ café',
            'uber': '🚗 Uber',
            '99': '🚗 99',
            'ifood': '🍔 iFood',
            'rappi': '🍔 Rappi',
            'netflix': '🎬 Netflix',
            'spotify': '🎵 Spotify',
            'amazon': '📦 Amazon',
            'cinema': '🎬 cinema',
            'academia': '💪 academia',
            'viagem': '✈️ viagens'
        }
        
        for palavra, emoji_texto in palavras_interesse.items():
            count = db.query(func.count(Lancamento.id)).filter(
                and_(
                    Lancamento.id_usuario == usuario_id,
                    Lancamento.tipo == 'Saída',
                    extract('year', Lancamento.data_transacao) == ano,
                    Lancamento.descricao.ilike(f'%{palavra}%')
                )
            ).scalar() or 0
            
            if count > 0:
                frequencia = count / 12  # Média por mês
                if frequencia >= 1:
                    curiosidades.append(
                        f"{emoji_texto}: {count} vezes no ano ({frequencia:.1f}x por mês em média)"
                    )
        
        # Dia da semana preferido para gastar
        # (necessita de análise mais complexa - simplificado)
        
        # Categoria mais frequente
        categoria_freq = db.query(
            Categoria.nome,
            func.count(Lancamento.id).label('vezes')
        ).join(
            Lancamento, Lancamento.id_categoria == Categoria.id
        ).filter(
            and_(
                Lancamento.id_usuario == usuario_id,
                Lancamento.tipo == 'Saída',
                extract('year', Lancamento.data_transacao) == ano
            )
        ).group_by(Categoria.nome).order_by(desc('vezes')).first()
        
        if categoria_freq:
            curiosidades.append(
                f"📊 Sua categoria favorita: {categoria_freq.nome} ({categoria_freq.vezes} transações)"
            )
        
        return curiosidades
    finally:
        db.close()


def comparar_com_ano_anterior(usuario_id: int, ano_atual: int) -> Optional[Dict]:
    """Compara estatísticas com o ano anterior"""
    db = next(get_db())
    try:
        ano_anterior = ano_atual - 1
        
        # Verificar se há dados do ano anterior
        tem_dados_anterior = db.query(func.count(Lancamento.id)).filter(
            and_(
                Lancamento.id_usuario == usuario_id,
                extract('year', Lancamento.data_transacao) == ano_anterior
            )
        ).scalar() > 0
        
        if not tem_dados_anterior:
            return None
        
        # Calcular estatísticas de ambos os anos
        stats_atual = calcular_resumo_financeiro(usuario_id, ano_atual)
        stats_anterior = calcular_resumo_financeiro(usuario_id, ano_anterior)
        
        # Calcular variações percentuais
        var_receitas = ((stats_atual['receitas_total'] - stats_anterior['receitas_total']) / 
                       stats_anterior['receitas_total'] * 100) if stats_anterior['receitas_total'] > 0 else 0
        
        var_despesas = ((stats_atual['despesas_total'] - stats_anterior['despesas_total']) / 
                       stats_anterior['despesas_total'] * 100) if stats_anterior['despesas_total'] > 0 else 0
        
        var_economia = ((stats_atual['economia_total'] - stats_anterior['economia_total']) / 
                       abs(stats_anterior['economia_total']) * 100) if stats_anterior['economia_total'] != 0 else 0
        
        return {
            'ano_anterior': ano_anterior,
            'var_receitas': var_receitas,
            'var_despesas': var_despesas,
            'var_economia': var_economia,
            'stats_anterior': stats_anterior,
            'melhorou': stats_atual['taxa_poupanca'] > stats_anterior['taxa_poupanca']
        }
    finally:
        db.close()


# ============================================================================
# FORMATAÇÃO DA MENSAGEM WRAPPED
# ============================================================================

def avaliar_performance_poupanca(taxa: float) -> Tuple[str, str]:
    """Retorna emoji e avaliação baseado na taxa de poupança"""
    if taxa >= 30:
        return "🏆", "EXCEPCIONAL"
    elif taxa >= 20:
        return "🌟", "EXCELENTE"
    elif taxa >= 10:
        return "👏", "MUITO BOM"
    elif taxa >= 5:
        return "👍", "BOM"
    elif taxa > 0:
        return "💪", "PODE MELHORAR"
    else:
        return "⚠️", "ATENÇÃO NECESSÁRIA"


def formatar_wrapped_completo(usuario: Usuario, ano: int) -> str:
    """
    Gera a mensagem completa do Wrapped Anual
    Esta é a mensagem ÉPICA que será enviada aos usuários!
    """
    try:
        # Coletar todas as estatísticas
        resumo = calcular_resumo_financeiro(usuario.id, ano)
        categorias_top = calcular_categorias_top(usuario.id, ano, 5)
        melhor_mes = encontrar_melhor_mes(usuario.id, ano)
        maior_gasto = encontrar_maior_gasto(usuario.id, ano)
        metas = calcular_metas_ano(usuario.id, ano)
        uso = calcular_estatisticas_uso(usuario.id, ano)
        curiosidades = gerar_curiosidades(usuario.id, ano)
        comparacao = comparar_com_ano_anterior(usuario.id, ano)
        
        # Avaliar performance
        emoji_perf, avaliacao_perf = avaliar_performance_poupanca(resumo['taxa_poupanca'])
        
        # Construir mensagem épica
        mensagem = f"""
🎆✨ <b>SEU ANO FINANCEIRO {ano} EM NÚMEROS!</b> ✨🎆

Olá, <b>{usuario.nome_completo}</b>! 

Que jornada incrível você teve neste ano! 🚀
Vamos relembrar tudo que você conquistou?

━━━━━━━━━━━━━━━━━━━━━━━━━━
💰 <b>RESUMO GERAL</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━

📈 Receitas: <code>R$ {resumo['receitas_total']:,.2f}</code>
📉 Despesas: <code>R$ {resumo['despesas_total']:,.2f}</code>
✨ Você economizou: <code>R$ {resumo['economia_total']:,.2f}</code>

{emoji_perf} Sua taxa de poupança foi <b>{avaliacao_perf}</b>: {resumo['taxa_poupanca']:.1f}%
"""

        # Comparação com ano anterior
        if comparacao:
            emoji_trend = "📈" if comparacao['melhorou'] else "📊"
            mensagem += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━
{emoji_trend} <b>COMPARAÇÃO COM {comparacao['ano_anterior']}</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━

"""
            if comparacao['var_receitas'] > 0:
                mensagem += f"📈 Receitas: +{comparacao['var_receitas']:.1f}% (cresceu!)\n"
            else:
                mensagem += f"📉 Receitas: {comparacao['var_receitas']:.1f}%\n"
            
            if comparacao['var_despesas'] < 0:
                mensagem += f"💚 Despesas: {comparacao['var_despesas']:.1f}% (economizou!)\n"
            else:
                mensagem += f"📊 Despesas: +{comparacao['var_despesas']:.1f}%\n"
            
            if comparacao['melhorou']:
                mensagem += f"\n🎉 <b>Parabéns! Você melhorou sua saúde financeira em {ano}!</b>\n"
        
        # Categorias top
        if categorias_top:
            mensagem += """
━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 <b>ONDE FOI SEU DINHEIRO</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━

"""
            for idx, cat in enumerate(categorias_top, 1):
                percentual = (cat['total'] / resumo['despesas_total'] * 100) if resumo['despesas_total'] > 0 else 0
                mensagem += f"{idx}. <b>{cat['categoria']}</b>\n"
                mensagem += f"   💰 R$ {cat['total']:,.2f} ({percentual:.1f}% do total)\n"
                mensagem += f"   🔢 {cat['quantidade']} transações\n\n"
        
        # Momentos marcantes
        mensagem += """
━━━━━━━━━━━━━━━━━━━━━━━━━━
😱 <b>MOMENTOS MARCANTES</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━

"""
        if maior_gasto:
            mensagem += f"💸 <b>Maior gasto do ano:</b>\n"
            mensagem += f"   {maior_gasto['descricao']}\n"
            mensagem += f"   R$ {maior_gasto['valor']:,.2f} em {maior_gasto['data']}\n\n"
        
        if melhor_mes['economia'] > 0:
            mensagem += f"💰 <b>Mês que mais economizou:</b>\n"
            mensagem += f"   {melhor_mes['nome']} (R$ {melhor_mes['economia']:,.2f})\n\n"
        
        # Metas
        if metas['metas_totais'] > 0:
            mensagem += """
━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 <b>METAS E CONQUISTAS</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━

"""
            mensagem += f"Você criou <b>{metas['metas_totais']} metas</b> em {ano}\n"
            mensagem += f"✅ Atingiu <b>{metas['metas_atingidas']}</b> delas ({metas['taxa_sucesso']:.0f}% de sucesso)\n\n"
            
            if metas['metas_atingidas'] > 0:
                mensagem += "<b>Metas conquistadas:</b>\n"
                for meta in metas['metas_detalhes']:
                    if meta['atingida']:
                        mensagem += f"  ✅ {meta['descricao']} - R$ {meta['valor_meta']:,.2f}\n"
                mensagem += "\n"
        
        # Curiosidades
        if curiosidades:
            mensagem += """
━━━━━━━━━━━━━━━━━━━━━━━━━━
🤯 <b>CURIOSIDADES SOBRE VOCÊ</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━

"""
            for curiosidade in curiosidades[:5]:  # Máximo 5
                mensagem += f"• {curiosidade}\n"
            mensagem += "\n"
        
        # Estatísticas de uso
        mensagem += """
━━━━━━━━━━━━━━━━━━━━━━━━━━
🎮 <b>SUA JORNADA NO MAESTROFIN</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━

"""
        mensagem += f"📝 Você registrou <b>{uso['total_lancamentos']} transações</b>\n"
        mensagem += f"📅 Usou o bot em <b>{uso['dias_ativos']} dias</b> (de 365)\n"
        
        if uso['conquistas'] > 0:
            mensagem += f"🏅 Desbloqueou <b>{uso['conquistas']} conquistas</b>\n"
        
        if uso['xp_total'] > 0:
            mensagem += f"⭐ Acumulou <b>{uso['xp_total']} XP</b> (Nível {uso['nivel_atual']})\n"
        
        # Mensagem inspiradora final
        ano_novo = ano + 1
        mensagem += f"""

━━━━━━━━━━━━━━━━━━━━━━━━━━
💝 <b>NOSSA MENSAGEM PARA VOCÊ</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━

Caro(a) {usuario.nome_completo},

<b>Obrigado por confiar em nós!</b> ❤️

Ter você conosco nesta jornada foi uma honra. 
Cada número que você viu aqui representa não apenas 
dinheiro, mas suas escolhas, seus sonhos e seu 
crescimento pessoal.

Você tomou o controle da sua vida financeira, e isso 
é algo <b>extraordinário</b>! 🌟

Enquanto muitos apenas sonham, você AGIU. Registrou 
gastos, criou metas, economizou, aprendeu. Isso te 
coloca entre os <b>poucos que realmente se importam</b> 
com o próprio futuro.

━━━━━━━━━━━━━━━━━━━━━━━━━━
🚀 <b>DESAFIO PARA {ano_novo}</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━

Com base nos seus dados, nossa IA sugere:
"""
        
        # Sugestão personalizada baseada nos dados
        if resumo['taxa_poupanca'] < 10:
            sugestao_meta = resumo['receitas_total'] * 0.15 / 12  # 15% anual dividido por 12
            mensagem += f"""
💡 <b>Meta de Poupança:</b>
   Tente economizar R$ {sugestao_meta:,.2f} por mês
   = R$ {sugestao_meta * 12:,.2f} no ano
   (15% da sua receita média)
"""
        elif resumo['taxa_poupanca'] < 20:
            sugestao_meta = resumo['receitas_total'] * 0.25 / 12  # 25% anual
            mensagem += f"""
💡 <b>Próximo Nível:</b>
   Você já economiza bem! Que tal aumentar para 
   R$ {sugestao_meta:,.2f} por mês?
   = R$ {sugestao_meta * 12:,.2f} no ano (25%)
"""
        else:
            mensagem += """
🏆 <b>Você é um MESTRE!</b>
   Sua disciplina financeira é inspiradora!
   Continue assim e considere investir suas economias
   para fazer o dinheiro trabalhar por você! 💰
"""
        
        # Encerramento épico
        mensagem += f"""

━━━━━━━━━━━━━━━━━━━━━━━━━━

✨ Que {ano_novo} seja o ano dos seus sonhos realizados!
✨ Que você alcance metas ainda maiores!
✨ Que a prosperidade esteja sempre ao seu lado!

Nós estaremos aqui, todos os dias, te apoiando 
nessa jornada. 🤝

<b>Feliz Ano Novo!</b> 🎊🎉
Com carinho e gratidão,
🎼 Equipe MaestroFin

───────────────────────────
<i>💡 Use /metas para criar seus objetivos de {ano_novo}!</i>
"""
        
        return mensagem
        
    except Exception as e:
        logger.error(f"❌ Erro ao gerar wrapped para usuário {usuario.id}: {e}", exc_info=True)
        return None


# ============================================================================
# JOB PRINCIPAL - EXECUTADO 31/DEZ ÀS 13H
# ============================================================================

async def job_wrapped_anual(context):
    """
    Job que roda automaticamente no dia 31 de dezembro às 13h
    Envia o Wrapped Financeiro para todos os usuários ativos
    """
    try:
        ano_atual = datetime.now().year
        logger.info(f"🎊 Iniciando envio do Wrapped Financeiro {ano_atual}...")
        
        db = next(get_db())
        
        # Buscar usuários com atividade no ano atual
        usuarios_ativos = db.query(Usuario).join(
            Lancamento, Usuario.id == Lancamento.id_usuario
        ).filter(
            extract('year', Lancamento.data_transacao) == ano_atual
        ).distinct().all()
        
        if not usuarios_ativos:
            logger.info("ℹ️  Nenhum usuário ativo para enviar wrapped")
            return
        
        total_usuarios = len(usuarios_ativos)
        enviados_sucesso = 0
        
        logger.info(f"📊 Gerando wrapped para {total_usuarios} usuários...")
        
        for usuario in usuarios_ativos:
            try:
                # Gerar mensagem personalizada
                mensagem = formatar_wrapped_completo(usuario, ano_atual)
                
                if mensagem:
                    # Enviar mensagem
                    await context.bot.send_message(
                        chat_id=usuario.telegram_id,
                        text=mensagem,
                        parse_mode='HTML'
                    )
                    enviados_sucesso += 1
                    
                    logger.info(f"✅ Wrapped enviado para {usuario.nome_completo}")
                    
                    # Pequeno delay para não sobrecarregar a API do Telegram
                    await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"❌ Erro ao enviar wrapped para usuário {usuario.id}: {e}")
                continue
        
        logger.info(
            f"🎊 Wrapped Financeiro {ano_atual} concluído: "
            f"{enviados_sucesso}/{total_usuarios} enviados com sucesso"
        )
        
    except Exception as e:
        logger.error(f"❌ Erro no job wrapped anual: {e}", exc_info=True)
    finally:
        db.close()


# ============================================================================
# FUNÇÃO DE TESTE MANUAL
# ============================================================================

async def enviar_wrapped_manual(bot, usuario: Usuario, ano: int = None):
    """
    Envia o wrapped para um usuário específico (para testes)
    Se ano não especificado, usa ano atual
    """
    try:
        if ano is None:
            ano = datetime.now().year
        
        mensagem = formatar_wrapped_completo(usuario, ano)
        
        if mensagem:
            await bot.send_message(
                chat_id=usuario.telegram_id,
                text=mensagem,
                parse_mode='HTML'
            )
            return True
        
        return False
    except Exception as e:
        logger.error(f"❌ Erro ao enviar wrapped manual: {e}", exc_info=True)
        return False
