# gerente_financeiro/services.py

import base64
import logging
import re
import io
import pandas as pd
from models import Conta, Objetivo, Agendamento
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, extract, text
import asyncio
import hashlib  # <-- Para gerar chaves de cache
import json  # <-- Para serialização de dados
from functools import lru_cache  # <-- Cache em memória
import time  # <-- Para timestamps do cache
import google.generativeai as genai
from .prompts import PROMPT_ANALISE_RELATORIO
from database.database import listar_objetivos_usuario
from models import Categoria, Lancamento, Usuario, Subcategoria
import config
from . import external_data
from dateutil.relativedelta import relativedelta
import numpy as np 
from scipy.interpolate import make_interp_spline

# --- SISTEMA DE CACHE INTELIGENTE V2 (OTIMIZADO) ---
_cache_financeiro = {}
_cache_tempo = {}
_cache_memoria = {}  # <-- Cache principal em memória
_cache_hash_transacoes = {}  # <-- Hash das transações para invalidação automática
CACHE_TTL = 30  # ⚡ 30 segundos (rápido para evitar dados desatualizados)
CACHE_MAX_SIZE = 100  # Limite de itens no cache

logger = logging.getLogger(__name__)

def _gerar_hash_transacoes(db: Session, user_id: int) -> str:
    """
    Gera hash único baseado na última modificação das transações.
    Qualquer mudança (nova, editada, deletada) invalida o cache.
    """
    from models import Lancamento
    from database.database import SessionLocal
    
    try:
        # Busca data da última modificação ou criação
        ultima_modificacao = db.query(
            func.max(Lancamento.data_transacao)
        ).filter(
            Lancamento.id_usuario == user_id
        ).scalar()
        
        total_transacoes = db.query(func.count(Lancamento.id)).filter(
            Lancamento.id_usuario == user_id
        ).scalar()
        
        # Hash baseado em data + total (muda se adicionar/remover)
        hash_data = f"{user_id}:{ultima_modificacao}:{total_transacoes}"
        return hashlib.md5(hash_data.encode()).hexdigest()
    except Exception as e:
        logger.warning(f"Erro ao gerar hash de transações: {e}")
        return f"{user_id}:{time.time()}"  # Fallback: nunca cachea

def _gerar_chave_cache(user_id: int, tipo: str, **parametros) -> str:
    """Gera uma chave única para cache baseada nos parâmetros"""
    dados_chave = {
        'user_id': user_id,
        'tipo': tipo,
        **parametros
    }
    texto_chave = json.dumps(dados_chave, sort_keys=True)
    return hashlib.md5(texto_chave.encode()).hexdigest()

def _cache_valido(chave: str, db: Session = None, user_id: int = None) -> bool:
    """
    Verifica se o cache ainda é válido.
    ⚡ NOVO: Invalida automaticamente se transações mudaram.
    """
    if chave not in _cache_tempo:
        return False
    
    # Verificar TTL (tempo)
    tempo_cache = _cache_tempo[chave]
    tempo_atual = datetime.now().timestamp()
    if (tempo_atual - tempo_cache) >= CACHE_TTL:
        logger.debug(f"❌ Cache expirado por TTL: {chave}")
        return False
    
    # ⚡ NOVO: Verificar se transações mudaram (invalidação inteligente)
    if db and user_id:
        hash_atual = _gerar_hash_transacoes(db, user_id)
        hash_cache = _cache_hash_transacoes.get(chave)
        
        if hash_cache and hash_cache != hash_atual:
            logger.info(f"🔄 Cache invalidado (transações mudaram): user {user_id}")
            # Remove do cache imediatamente
            _cache_financeiro.pop(chave, None)
            _cache_tempo.pop(chave, None)
            _cache_hash_transacoes.pop(chave, None)
            return False
    
    return True

def _obter_do_cache(chave: str, db: Session = None, user_id: int = None) -> Any:
    """
    Obtém dados do cache se válido.
    ⚡ NOVO: Valida se transações mudaram antes de retornar.
    """
    if _cache_valido(chave, db, user_id):
        logger.debug(f"✅ Cache hit: {chave}")
        return _cache_financeiro.get(chave)
    
    logger.debug(f"❌ Cache miss: {chave}")
    return None

def _salvar_no_cache(chave: str, dados: Any, db: Session = None, user_id: int = None) -> None:
    """
    Salva dados no cache com timestamp e hash das transações.
    ⚡ NOVO: Salva hash para invalidação automática.
    """
    # Limita tamanho do cache
    if len(_cache_financeiro) >= CACHE_MAX_SIZE:
        # Remove item mais antigo
        chave_mais_antiga = min(_cache_tempo.items(), key=lambda x: x[1])[0]
        _cache_financeiro.pop(chave_mais_antiga, None)
        _cache_tempo.pop(chave_mais_antiga, None)
        _cache_hash_transacoes.pop(chave_mais_antiga, None)
        logger.debug(f"🗑️ Cache limpo (limite atingido): {chave_mais_antiga}")
    
    _cache_financeiro[chave] = dados
    _cache_tempo[chave] = datetime.now().timestamp()
    
    # ⚡ NOVO: Salva hash das transações para invalidação automática
    if db and user_id:
        _cache_hash_transacoes[chave] = _gerar_hash_transacoes(db, user_id)
    
    logger.debug(f"💾 Dados salvos no cache: {chave}")
    
def limpar_cache_usuario(user_id: int) -> None:
    """Limpa todo o cache de um usuário específico"""
    chaves_para_remover = [
        chave for chave in _cache_financeiro.keys() 
        if str(user_id) in chave
    ]
    for chave in chaves_para_remover:
        _cache_financeiro.pop(chave, None)
        _cache_tempo.pop(chave, None)

logger = logging.getLogger(__name__)

CSE_ID  = config.GOOGLE_CSE_ID
API_KEY = config.GOOGLE_API_KEY

INTENT_PATTERNS = {
    "dólar": r"\b(d[óo]lar|usd)\b",
    "euro": r"\b(euro|eur)\b",
    "bitcoin": r"\b(bitcoin|btc)\b",
    "gasolina": r"\b(gasolina|combust[íi]vel)\b",
    "selic": r"\b(selic)\b",
    "ipca": r"\b(ipca)\b",
}

# =========================================================================
#  FUNÇÃO ESSENCIAL QUE ESTAVA FALTANDO
# =========================================================================

def preparar_contexto_json(lancamentos: List[Lancamento]) -> str:
    """
    Converte uma lista de objetos Lancamento em uma string JSON formatada,
    que é o formato que a IA do Gemini espera receber.
    """
    if not lancamentos:
        return "[]"
    
    lista_para_json = []
    for lanc in lancamentos:
        lanc_dict = {
            "id": lanc.id,
            "descricao": lanc.descricao,
            "valor": float(lanc.valor),
            "tipo": lanc.tipo,
            "data_transacao": lanc.data_transacao.isoformat(),
            "forma_pagamento": lanc.forma_pagamento,
            "categoria_nome": lanc.categoria.nome if lanc.categoria else "Sem Categoria",
            "subcategoria_nome": lanc.subcategoria.nome if lanc.subcategoria else None,
            "itens": [
                {"nome_item": item.nome_item, "quantidade": float(item.quantidade or 1), "valor_unitario": float(item.valor_unitario or 0)}
                for item in lanc.itens
            ] if lanc.itens else []
        }
        lista_para_json.append(lanc_dict)
    
    return json.dumps(lista_para_json, indent=2, ensure_ascii=False)



def gerar_grafico_para_relatorio(gastos_por_categoria: dict) -> io.BytesIO | None:
    """Gera um gráfico de pizza a partir de um dicionário de gastos por categoria."""
    if not gastos_por_categoria:
        return None

    try:
        plt.style.use('seaborn-v0_8-whitegrid')
        
        df = pd.DataFrame(list(gastos_por_categoria.items()), columns=['Categoria', 'Valor']).sort_values('Valor', ascending=False)
        
        if len(df) > 6:
            top_5 = df.iloc[:5].copy()
            outros_valor = df.iloc[5:]['Valor'].sum()
            outros_df = pd.DataFrame([{'Categoria': 'Outros', 'Valor': outros_valor}])
            df = pd.concat([top_5, outros_df], ignore_index=True)

        fig, ax = plt.subplots(figsize=(8, 5), dpi=100)
        
        colors = sns.color_palette("viridis_r", len(df))
        
        wedges, _, autotexts = ax.pie(
            df['Valor'], 
            autopct='%1.1f%%', 
            startangle=140, 
            pctdistance=0.85, 
            colors=colors, 
            wedgeprops={'edgecolor': 'white', 'linewidth': 1.5}
        )
        plt.setp(autotexts, size=10, weight="bold", color="white")
        
        centre_circle = plt.Circle((0,0),0.70,fc='white')
        fig.gca().add_artist(centre_circle)
        
        ax.set_title('Distribuição de Despesas', fontsize=16, pad=15, weight='bold')
        ax.axis('equal')

        plt.tight_layout()
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', bbox_inches='tight')
        buffer.seek(0)
        return buffer
    except Exception as e:
        logger.error(f"Erro CRÍTICO ao gerar gráfico para relatório: {e}", exc_info=True)
        return None
    finally:
        plt.close('all')

def gerar_contexto_relatorio(db: Session, telegram_id: int, mes: int, ano: int):
    """
    Coleta e processa dados detalhados para o relatório avançado, ignorando
    transações da categoria 'Transferência' para os cálculos financeiros.
    """
    
    usuario_q = db.query(Usuario).filter(Usuario.telegram_id == telegram_id).first()
    if not usuario_q: 
        logging.warning(f"Usuário com telegram_id {telegram_id} não encontrado para gerar relatório.")
        return None

    data_alvo = datetime(ano, mes, 1)
    periodo_alvo = pd.Period(data_alvo, freq='M')

    # Busca todos os lançamentos do período, incluindo transferências
    lancamentos_mes_atual = db.query(Lancamento).filter(
        and_(
            Lancamento.id_usuario == usuario_q.id,
            extract('year', Lancamento.data_transacao) == ano,
            extract('month', Lancamento.data_transacao) == mes
        )
    ).options(joinedload(Lancamento.categoria)).all()

    # Busca histórico de 6 meses usando extract para evitar problemas de timezone
    from sqlalchemy import or_
    historico_conditions = []
    temp_date = data_alvo
    for _ in range(6):
        historico_conditions.append(
            and_(
                extract('year', Lancamento.data_transacao) == temp_date.year,
                extract('month', Lancamento.data_transacao) == temp_date.month
            )
        )
        temp_date -= relativedelta(months=1)

    lancamentos_historico_6m = db.query(Lancamento).filter(
        and_(
            Lancamento.id_usuario == usuario_q.id,
            or_(*historico_conditions)
        )
    ).options(joinedload(Lancamento.categoria)).all()

    mes_nome_str = data_alvo.strftime("%B").capitalize()

    if not lancamentos_mes_atual:
        return {"has_data": False, "usuario": usuario_q, "mes_nome": mes_nome_str, "ano": ano, "now": datetime.now}
    
    # --- CORREÇÃO APLICADA: FILTRAGEM DE TRANSFERÊNCIAS ---
    # Cria uma nova lista contendo apenas lançamentos que NÃO são transferências
    lancamentos_financeiros = [
        l for l in lancamentos_mes_atual 
        if not (l.categoria and l.categoria.nome.lower() == 'transferência')
    ]

    # Todos os cálculos de receita, despesa e saldo agora usam a lista filtrada
    receitas_atual = sum(float(l.valor) for l in lancamentos_financeiros if l.tipo == 'Receita')
    despesas_atual = sum(float(l.valor) for l in lancamentos_financeiros if l.tipo == 'Despesa')
    saldo_atual = receitas_atual - despesas_atual
    taxa_poupanca_atual = (saldo_atual / receitas_atual) * 100 if receitas_atual > 0 else 0

    # O agrupamento de gastos também usa a lista filtrada
    gastos_por_categoria_atual = {}
    for l in lancamentos_financeiros:
        if l.tipo == 'Despesa' and l.valor > 0:
            cat_nome = l.categoria.nome if l.categoria else "Sem Categoria"
            gastos_por_categoria_atual[cat_nome] = gastos_por_categoria_atual.get(cat_nome, 0) + float(l.valor)
    
    gastos_agrupados_final = sorted([(cat, val) for cat, val in gastos_por_categoria_atual.items()], key=lambda i: i[1], reverse=True)

    # A análise histórica pode continuar usando todos os dados, se desejado, ou também pode ser filtrada
    df_historico = pd.DataFrame([
        {'data': l.data_transacao, 'valor': float(l.valor), 'tipo': l.tipo} 
        for l in lancamentos_historico_6m 
        if not (l.categoria and l.categoria.nome.lower() == 'transferência') # Filtrando aqui também
    ])
    
    if not df_historico.empty:
        df_historico['mes_ano'] = df_historico['data'].dt.to_period('M')
        dados_mensais = df_historico.groupby(['mes_ano', 'tipo'])['valor'].sum().unstack(fill_value=0)
    else:
        dados_mensais = pd.DataFrame()
        
    if 'Receita' not in dados_mensais.columns: dados_mensais['Receita'] = 0
    if 'Despesa' not in dados_mensais.columns: dados_mensais['Despesa'] = 0

    periodo_3m = dados_mensais.index[dados_mensais.index < periodo_alvo][-3:]
    media_3m = dados_mensais.loc[periodo_3m].mean() if not periodo_3m.empty else pd.Series(dtype=float)
    media_receitas_3m = media_3m.get('Receita', 0.0)
    media_despesas_3m = media_3m.get('Despesa', 0.0)

    periodo_anterior = periodo_alvo - 1
    if periodo_anterior in dados_mensais.index:
        receitas_anterior = dados_mensais.loc[periodo_anterior, 'Receita']
        despesas_anterior = dados_mensais.loc[periodo_anterior, 'Despesa']
        tendencia_receita_percent = ((receitas_atual - receitas_anterior) / receitas_anterior * 100) if receitas_anterior > 0 else 0
        tendencia_despesa_percent = ((despesas_atual - despesas_anterior) / despesas_anterior * 100) if despesas_anterior > 0 else 0
    else:
        tendencia_receita_percent = 0
        tendencia_despesa_percent = 0

    # Placeholders para futuras implementações
    analise_ia = "Análise inteligente do Maestro aparecerá aqui."
    metas_com_progresso = []

    contexto = {
        "has_data": True, "now": datetime.now, "usuario": usuario_q,
        "mes_nome": mes_nome_str, "ano": ano,
        "receita_total": receitas_atual,
        "despesa_total": despesas_atual,
        "saldo_mes": saldo_atual,
        "taxa_poupanca": taxa_poupanca_atual,
        "gastos_agrupados": gastos_agrupados_final,
        "gastos_por_categoria_dict": gastos_por_categoria_atual,
        "lancamentos_historico": lancamentos_historico_6m, # Mantém o histórico completo para referência
        "tendencia_receita_percent": tendencia_receita_percent,
        "tendencia_despesa_percent": tendencia_despesa_percent,
        "media_receitas_3m": media_receitas_3m,
        "media_despesas_3m": media_despesas_3m,
        "media_saldo_3m": media_receitas_3m - media_despesas_3m,
        "analise_ia": analise_ia,
        "metas": metas_com_progresso,
    }
    
    return contexto

def gerar_grafico_evolucao_mensal(lancamentos_historico: list) -> io.BytesIO | None:
    if not lancamentos_historico:
        return None

    try:
        dados = []
        for l in lancamentos_historico:
            dados.append({
                'data': l.data_transacao,
                'valor': float(l.valor),
                'tipo': l.tipo
            })
        
        df = pd.DataFrame(dados)
        df['mes_ano'] = df['data'].dt.to_period('M')

        df_agrupado = df.groupby(['mes_ano', 'tipo'])['valor'].sum().unstack(fill_value=0)
        
        if 'Receita' not in df_agrupado.columns: df_agrupado['Receita'] = 0
        if 'Despesa' not in df_agrupado.columns: df_agrupado['Despesa'] = 0
        
        df_agrupado = df_agrupado.sort_index()
        
        df_agrupado.index = df_agrupado.index.strftime('%b/%y')

        fig, ax = plt.subplots(figsize=(10, 5), dpi=100)
        
        ax.plot(df_agrupado.index, df_agrupado['Receita'], marker='o', linestyle='-', color='#2ecc71', label='Receitas')
        ax.plot(df_agrupado.index, df_agrupado['Despesa'], marker='o', linestyle='-', color='#e74c3c', label='Despesas')

        ax.set_title('Receitas vs. Despesas (Últimos 6 Meses)', fontsize=16, weight='bold')
        ax.set_ylabel('Valor (R$)')
        ax.grid(True, which='both', linestyle='--', linewidth=0.5)
        ax.legend()
        
        plt.tight_layout()
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', bbox_inches='tight')
        buffer.seek(0)
        return buffer
    except Exception as e:
        logger.error(f"Erro ao gerar gráfico de evolução: {e}", exc_info=True)
        return None
    finally:
        plt.close('all')

def detectar_intencao_e_topico(pergunta: str) -> Optional[tuple[str, str]]:
    pergunta_lower = pergunta.lower()
    for topico_base, padrao in INTENT_PATTERNS.items():
        if re.search(padrao, pergunta_lower, re.I):
            flag = topico_base
            if flag == 'dólar': 
                flag = 'usd'
            
            nome_topico = topico_base.capitalize()
            if nome_topico == 'Dólar': 
                nome_topico = "Cotação do Dólar"
            elif nome_topico == 'Euro': 
                nome_topico = "Cotação do Euro"
            elif nome_topico == 'Gasolina': 
                nome_topico = "Preço da Gasolina"
            elif nome_topico == 'Ipca': 
                nome_topico = "Taxa IPCA"
            elif nome_topico == 'Selic': 
                nome_topico = "Taxa Selic"
            
            return flag, nome_topico
    return None, None

async def obter_dados_externos(flag: str) -> dict:
    logger.info(f"Buscando dados externos para a flag: '{flag}'")
    resultado_html = None
    fonte = "N/A"
    topico = flag.capitalize()
    now = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=-3))).strftime('%d/%m/%Y %H:%M')
    try:
        if flag == 'usd':
            topico = "Cotação do Dólar"
            preco = await external_data.get_exchange_rate("USD/BRL")
            if preco:
                resultado_html = f"💵 <b>{topico}:</b> <code>R$ {preco:.2f}</code>"
                fonte = "AwesomeAPI"
        elif flag == 'gasolina':
            topico = "Preço da Gasolina"
            preco = await external_data.get_gas_price()
            if preco:
                resultado_html = f"⛽️ <b>{topico}:</b> <code>R$ {preco:.3f}</code>"
                fonte = "Fonte de Exemplo"
        if not resultado_html:
            logger.warning(f"API específica para '{flag}' falhou ou não existe. Usando Google Search como fallback.")
            fonte = "Google Custom Search"
            termos_busca_map = {
                'usd': ("Cotação do Dólar", "cotação atual do dólar"),
                'gasolina': ("Preço da Gasolina", "preço médio da gasolina no brasil hoje")
            }
            topico, termo_busca = termos_busca_map.get(flag, (f"Busca por {flag.title()}", f"cotação atual de {flag}"))
            r = await external_data.google_search(termo_busca, API_KEY, CSE_ID, top=1)
            if r and r.get("items"):
                item = r["items"][0]
                titulo = item.get("title", "Sem título")
                snippet = item.get("snippet", "Sem descrição.")
                preco_match = re.search(r'R\$\s*(\d+[,.]\d{2,3})', snippet)
                if preco_match:
                    preco_encontrado = preco_match.group(1).replace(',', '.')
                    emoji = "⛽️" if flag == 'gasolina' else "💲"
                    resultado_html = f"{emoji} <b>{topico} (aprox.):</b> <code>R$ {preco_encontrado}</code>"
                else:
                    resultado_html = f"<b>{titulo}</b>\n<i>{snippet[:150]}...</i>"
            else:
                resultado_html = f"A busca no Google para '{termo_busca}' não retornou resultados."
    except Exception as e:
        logger.error(f"Erro ao buscar dados externos para '{flag}': {e}", exc_info=True)
        resultado_html = f"Ocorreu um erro ao tentar pesquisar por '{flag}'."
    texto_final = f"{resultado_html}\n\n📊 <b>Fonte:</b> {fonte}\n🕐 <b>Consulta:</b> {now}"
    return {"texto_html": texto_final, "topico": topico}

async def obter_contexto_macroeconomico() -> str:
    try:
        indicadores = await asyncio.to_thread(external_data.get_indicadores_financeiros)
        if indicadores:
            return f"Selic: {indicadores.get('selic_meta_anual', 'N/A')}%, IPCA (12m): {indicadores.get('ipca_acumulado_12m', 'N/A')}%"
    except Exception as e:
        logger.warning(f"Não foi possível obter contexto macroeconômico: {e}")
    return "Contexto macroeconômico indisponível no momento."

async def gerar_analise_personalizada(info: str, perfil: str) -> str:
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")  # ✅ Modelo 2.5 (v1beta)
        prompt = f"Em uma frase, explique o impacto desta notícia/dado para um investidor de perfil {perfil}: {info}"
        resposta = await model.generate_content_async(prompt)
        return resposta.text.strip()
    except Exception as e:
        logger.error(f"Erro ao gerar análise personalizada com Gemini: {e}")
        return "(Não foi possível gerar a análise.)"

def get_category_emoji(category_name: str) -> str:
    emoji_map = {
        'Alimentação': '🍔', 'Transporte': '🚗', 'Moradia': '🏠', 'Saúde': '❤️‍🩹',
        'Lazer': '🎉', 'Educação': '📚', 'Serviços': '💻', 'Outros': '🏷️',
        'Compras': '🛍️', 'Investimentos': '📈', 'Impostos e Taxas': '🧾',
        'Cuidados Pessoais': '💅', 'Sem Categoria': '❓'
    }
    return emoji_map.get(category_name, '💸')

def buscar_lancamentos_com_relacionamentos(db: Session, telegram_id: int) -> List[Lancamento]:
    logger.info(f"Buscando lançamentos com relacionamentos para telegram_id: {telegram_id}")
    lancamentos = db.query(Lancamento).join(Usuario).options(
        joinedload(Lancamento.categoria),
        joinedload(Lancamento.subcategoria)
    ).filter(
        Usuario.telegram_id == telegram_id
    ).order_by(Lancamento.data_transacao.desc()).limit(200).all()
    logger.info(f"Consulta ao DB finalizada. Encontrados {len(lancamentos)} lançamentos para o telegram_id: {telegram_id}")
    return lancamentos

def analisar_comportamento_financeiro(lancamentos: List[Lancamento]) -> Dict[str, Any]:
    """
    Análise comportamental financeira avançada - VERSÃO 2.0
    Inclui detecção de anomalias, padrões sazonais e projeções
    """
    if not lancamentos:
        return {"has_data": False}
    
    # Preparação de dados com mais informações
    dados_lancamentos = []
    for l in lancamentos:
        dados_lancamentos.append({
            'valor': float(l.valor),
            'tipo': l.tipo,
            'data_transacao': l.data_transacao,
            'categoria_nome': l.categoria.nome if l.categoria else 'Sem Categoria',
            'dia_semana': l.data_transacao.weekday(),
            'hora': l.data_transacao.hour
        })
    
    df = pd.DataFrame(dados_lancamentos)
    df['data_transacao'] = pd.to_datetime(df['data_transacao']).dt.tz_localize(None)
    
    despesas_df = df[df['tipo'] == 'Despesa'].copy()
    receitas_df = df[df['tipo'] == 'Receita'].copy()
    
    if despesas_df.empty:
        return {"has_data": False, "total_receitas_90d": float(receitas_df['valor'].sum())}
    
    # === ANÁLISES BÁSICAS (mantidas) ===
    total_despesas = despesas_df['valor'].sum()
    total_receitas = receitas_df['valor'].sum()
    
    top_categoria = despesas_df.groupby('categoria_nome')['valor'].sum().nlargest(1)
    
    hoje = datetime.now()
    ultimos_30_dias = despesas_df[despesas_df['data_transacao'] > (hoje - timedelta(days=30))]
    periodo_anterior = despesas_df[(despesas_df['data_transacao'] <= (hoje - timedelta(days=30))) & 
                                   (despesas_df['data_transacao'] > (hoje - timedelta(days=60)))]
    
    gasto_recente = ultimos_30_dias['valor'].sum()
    gasto_anterior = periodo_anterior['valor'].sum()
    
    tendencia = "estável"
    percentual_mudanca = 0
    if gasto_anterior > 0:
        percentual_mudanca = ((gasto_recente - gasto_anterior) / gasto_anterior) * 100
        if percentual_mudanca > 10:
            tendencia = f"aumento de {percentual_mudanca:.0f}%"
        elif percentual_mudanca < -10:
            tendencia = f"redução de {abs(percentual_mudanca):.0f}%"
    
    # === ANÁLISES AVANÇADAS (novas) ===
    
    # 1. Análise por dia da semana
    gastos_por_dia_semana = despesas_df.groupby('dia_semana')['valor'].sum()
    dia_mais_gasto = gastos_por_dia_semana.idxmax() if not gastos_por_dia_semana.empty else None
    dias_semana = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']
    
    # 2. Análise por período do dia
    despesas_df['periodo_dia'] = despesas_df['hora'].apply(lambda h: 
        'Manhã' if 6 <= h < 12 else
        'Tarde' if 12 <= h < 18 else
        'Noite' if 18 <= h < 24 else
        'Madrugada'
    )
    gastos_por_periodo = despesas_df.groupby('periodo_dia')['valor'].sum()
    periodo_mais_gasto = gastos_por_periodo.idxmax() if not gastos_por_periodo.empty else None
    
    # 3. Detecção de anomalias (gastos muito acima da média)
    if len(despesas_df) > 5:
        Q1 = despesas_df['valor'].quantile(0.25)
        Q3 = despesas_df['valor'].quantile(0.75)
        IQR = Q3 - Q1
        limite_superior = Q3 + 1.5 * IQR
        anomalias = despesas_df[despesas_df['valor'] > limite_superior]
        num_anomalias = len(anomalias)
        valor_anomalias = anomalias['valor'].sum() if not anomalias.empty else 0
    else:
        num_anomalias = 0
        valor_anomalias = 0
    
    # 4. Análise de frequência de categorias
    freq_categorias = despesas_df['categoria_nome'].value_counts()
    categoria_mais_frequente = freq_categorias.index[0] if not freq_categorias.empty else "N/A"
    
    # 5. Cálculos de projeção melhorados
    economia_total_periodo = total_receitas - total_despesas
    dias_de_dados = (df['data_transacao'].max() - df['data_transacao'].min()).days + 1
    meses_de_dados = max(1, dias_de_dados / 30.0)
    economia_media_mensal = economia_total_periodo / meses_de_dados
    
    valor_maior_gasto = float(top_categoria.iloc[0]) if not top_categoria.empty else 0.0
    valor_reducao_sugerida = valor_maior_gasto * 0.15
    
    meses_para_meta_base = (5000 / economia_media_mensal) if economia_media_mensal > 0 else float('inf')
    meses_para_meta_otimizada = (5000 / (economia_media_mensal + valor_reducao_sugerida)) if (economia_media_mensal + valor_reducao_sugerida) > 0 else float('inf')
    
    # 6. Score de saúde financeira (0-100)
    score_saude = 50  # Base
    if economia_media_mensal > 0: score_saude += 20
    if tendencia.startswith("redução"): score_saude += 15
    if num_anomalias == 0: score_saude += 10
    if abs(percentual_mudanca) < 5: score_saude += 5  # Estabilidade
    score_saude = min(100, max(0, score_saude))
    
    return {
        "has_data": True,
        # === DADOS BÁSICOS ===
        "total_despesas_90d": float(total_despesas),
        "total_receitas_90d": float(total_receitas),
        "categoria_maior_gasto": top_categoria.index[0] if not top_categoria.empty else "N/A",
        "valor_maior_gasto": valor_maior_gasto,
        "tendencia_gastos_30d": tendencia,
        "percentual_mudanca": percentual_mudanca,
        "economia_media_mensal": float(economia_media_mensal),
        "valor_reducao_sugerida": float(valor_reducao_sugerida),
        "meses_para_meta_base": meses_para_meta_base,
        "meses_para_meta_otimizada": meses_para_meta_otimizada,
        
        # === DADOS AVANÇADOS ===
        "dia_semana_mais_gasto": dias_semana[dia_mais_gasto] if dia_mais_gasto is not None else "N/A",
        "periodo_dia_mais_gasto": periodo_mais_gasto or "N/A",
        "numero_anomalias": num_anomalias,
        "valor_anomalias": float(valor_anomalias),
        "categoria_mais_frequente": categoria_mais_frequente,
        "frequencia_categoria_top": int(freq_categorias.iloc[0]) if not freq_categorias.empty else 0,
        "score_saude_financeira": score_saude,
        "periodo_analise_dias": dias_de_dados,
        
        # === INSIGHTS ACIONÁVEIS ===
        "insights": [
            f"Você gasta mais às {dias_semana[dia_mais_gasto] if dia_mais_gasto is not None else 'N/A'}",
            f"Período do dia com mais gastos: {periodo_mais_gasto or 'N/A'}",
            f"Score de saúde financeira: {score_saude}/100",
            f"Detectadas {num_anomalias} transações atípicas" if num_anomalias > 0 else "Nenhuma transação atípica detectada"
        ]
    }

# --- FUNÇÕES GENÉRICAS PARA ELIMINAÇÃO DE DUPLICAÇÃO ---

async def salvar_transacoes_generica(db: Session, usuario_db, transacoes: list, 
                                   conta_id: int, tipo_origem: str = "manual") -> tuple[bool, str, dict]:
    """
    Função genérica para salvar transações em lote.
    Elimina duplicação entre extrato_handler e fatura_handler.
    
    Args:
        db: Sessão do banco de dados
        usuario_db: Objeto Usuario do banco
        transacoes: Lista de dicionários com dados das transações
        conta_id: ID da conta associada
        tipo_origem: Tipo da origem ('extrato', 'fatura', 'manual')
    
    Returns:
        tuple: (sucesso: bool, mensagem: str, estatisticas: dict)
    """
    try:
        # Verifica se a conta existe e pertence ao usuário
        conta = db.query(Conta).filter(
            Conta.id == conta_id, 
            Conta.id_usuario == usuario_db.id
        ).first()
        
        if not conta:
            return False, "Conta não encontrada ou não pertence ao usuário.", {}
        
        # Estatísticas de processamento
        stats = {
            'total_enviadas': len(transacoes),
            'salvas': 0,
            'duplicadas': 0,
            'erro': 0,
            'valor_total': 0.0
        }
        
        transacoes_salvas = []
        
        for transacao_data in transacoes:
            try:
                # Verifica duplicidade primeiro
                if verificar_duplicidade_transacoes(db, usuario_db.id, conta_id, transacao_data):
                    stats['duplicadas'] += 1
                    continue
                
                # Prepara os dados da transação
                lancamento_data = _preparar_dados_lancamento(transacao_data, usuario_db.id, conta_id)
                
                # Cria o lançamento
                novo_lancamento = Lancamento(**lancamento_data)
                db.add(novo_lancamento)
                
                transacoes_salvas.append(novo_lancamento)
                stats['salvas'] += 1
                stats['valor_total'] += float(lancamento_data.get('valor', 0))
                
            except Exception as e:
                logging.error(f"Erro ao processar transação individual: {e}")
                stats['erro'] += 1
                continue
        
        # Commit das transações
        db.commit()
        
        # Gera mensagem de resultado
        mensagem_resultado = _gerar_mensagem_resultado_salvamento(stats, tipo_origem)
        
        return True, mensagem_resultado, stats
        
    except Exception as e:
        db.rollback()
        logging.error(f"Erro crítico em salvar_transacoes_generica: {e}")
        return False, f"Erro ao salvar transações: {str(e)}", {}


def verificar_duplicidade_transacoes(db: Session, user_id: int, conta_id: int, 
                                   transacao_data: dict, janela_dias: int = 3) -> bool:
    """
    Verifica se uma transação já existe para evitar duplicatas.
    
    Args:
        db: Sessão do banco
        user_id: ID do usuário
        conta_id: ID da conta
        transacao_data: Dados da transação a verificar
        janela_dias: Janela de dias para buscar duplicatas
    
    Returns:
        bool: True se encontrou duplicata, False caso contrário
    """
    try:
        # Extrai dados necessários
        valor = float(transacao_data.get('valor', 0))
        descricao = transacao_data.get('descricao', '').strip()
        data_transacao = transacao_data.get('data_transacao')
        
        # Converte data se necessário
        if isinstance(data_transacao, str):
            try:
                data_transacao = datetime.strptime(data_transacao, '%d/%m/%Y')
            except:
                data_transacao = datetime.strptime(data_transacao, '%Y-%m-%d')
        
        # Define janela de busca
        data_inicio = data_transacao - timedelta(days=janela_dias)
        data_fim = data_transacao + timedelta(days=janela_dias)
        
        # Busca por duplicatas
        duplicata = db.query(Lancamento).filter(
            Lancamento.id_usuario == user_id,
            Lancamento.id_conta == conta_id,
            Lancamento.valor == valor,
            Lancamento.data_transacao.between(data_inicio, data_fim)
        ).first()
        
        # Se encontrou duplicata com valor e data similar, verifica descrição
        if duplicata:
            # Compara descrições (similaridade básica)
            desc_existente = duplicata.descricao.lower().strip()
            desc_nova = descricao.lower().strip()
            
            # Se descrições são muito similares, considera duplicata
            if _calcular_similaridade_descricao(desc_existente, desc_nova) > 0.8:
                return True
        
        return False
        
    except Exception as e:
        logging.error(f"Erro ao verificar duplicidade: {e}")
        return False


def _preparar_dados_lancamento(transacao_data: dict, user_id: int, conta_id: int) -> dict:
    """
    Prepara dados da transação para criação do Lancamento.
    """
    # Mapeia campos comuns
    dados = {
        'id_usuario': user_id,
        'id_conta': conta_id,
        'valor': float(transacao_data.get('valor', 0)),
        'descricao': transacao_data.get('descricao', '').strip(),
        'data_transacao': transacao_data.get('data_transacao'),
        'tipo': transacao_data.get('tipo', 'Despesa'),
        'forma_pagamento': transacao_data.get('forma_pagamento', 'Não informado'),
        'id_categoria': transacao_data.get('id_categoria'),
        'id_subcategoria': transacao_data.get('id_subcategoria'),
        'origem': transacao_data.get('origem', 'manual')
    }
    
    # Converte data se necessário
    if isinstance(dados['data_transacao'], str):
        try:
            dados['data_transacao'] = datetime.strptime(dados['data_transacao'], '%d/%m/%Y')
        except:
            dados['data_transacao'] = datetime.strptime(dados['data_transacao'], '%Y-%m-%d')
    
    return dados


def _gerar_mensagem_resultado_salvamento(stats: dict, tipo_origem: str) -> str:
    """
    Gera mensagem de resultado do salvamento.
    """
    total = stats['total_enviadas']
    salvas = stats['salvas']
    duplicadas = stats['duplicadas']
    erro = stats['erro']
    valor_total = stats['valor_total']
    
    emoji_origem = {
        'manual': '✏️',
        'openfinance': '🏦'
    }.get(tipo_origem, '📝')
    
    msg = f"{emoji_origem} <b>Processamento concluído!</b>\n\n"
    msg += f"📊 <b>Resumo:</b>\n"
    msg += f"• <b>Total enviadas:</b> {total}\n"
    msg += f"• <b>✅ Salvas:</b> {salvas}\n"
    
    if duplicadas > 0:
        msg += f"• <b>🔄 Duplicadas (ignoradas):</b> {duplicadas}\n"
    
    if erro > 0:
        msg += f"• <b>❌ Com erro:</b> {erro}\n"
    
    if salvas > 0:
        msg += f"\n💰 <b>Valor total:</b> <code>R$ {valor_total:.2f}</code>\n"
        msg += f"\n✨ Suas transações foram organizadas automaticamente!"
    
    return msg


def _calcular_similaridade_descricao(desc1: str, desc2: str) -> float:
    """
    Calcula similaridade básica entre duas descrições.
    """
    if not desc1 or not desc2:
        return 0.0
    
    # Normaliza textos
    desc1 = re.sub(r'[^a-zA-Z0-9\s]', '', desc1.lower())
    desc2 = re.sub(r'[^a-zA-Z0-9\s]', '', desc2.lower())
    
    # Divide em palavras
    palavras1 = set(desc1.split())
    palavras2 = set(desc2.split())
    
    if not palavras1 or not palavras2:
        return 0.0
    
    # Calcula Jaccard similarity
    intersecao = len(palavras1.intersection(palavras2))
    uniao = len(palavras1.union(palavras2))
    
    return intersecao / uniao if uniao > 0 else 0.0


async def processar_transacoes_inteligente(db: Session, usuario_db, transacoes_raw: list,
                                         conta_id: int, tipo_origem: str = "manual") -> tuple[bool, str, dict]:
    """
    Processa transações com inteligência adicional (categorização automática, etc.).
    
    Args:
        db: Sessão do banco
        usuario_db: Usuário do banco
        transacoes_raw: Lista de transações brutas
        conta_id: ID da conta
        tipo_origem: Origem das transações
    
    Returns:
        tuple: (sucesso, mensagem, estatísticas)
    """
    # Categoriza automaticamente as transações
    transacoes_categorizadas = await _categorizar_transacoes_automaticamente(db, transacoes_raw)
    
    # Usa a função genérica de salvamento
    return await salvar_transacoes_generica(db, usuario_db, transacoes_categorizadas, conta_id, tipo_origem)


async def _categorizar_transacoes_automaticamente(db: Session, transacoes: list) -> list:
    """
    Categoriza transações automaticamente baseado na descrição.
    """
    # Mapeamento de palavras-chave para categorias
    mapeamento_categorias = {
        'alimentacao': ['restaurante', 'lanchonete', 'ifood', 'uber eats', 'supermercado', 'padaria'],
        'transporte': ['uber', '99', 'taxi', 'bus', 'metro', 'combustivel', 'gasolina'],
        'lazer': ['cinema', 'teatro', 'show', 'bar', 'festa', 'balada'],
        'saude': ['farmacia', 'medico', 'hospital', 'clinica', 'exame'],
        'compras': ['loja', 'shopping', 'mercado livre', 'amazon', 'magazine'],
        'moradia': ['aluguel', 'condominio', 'luz', 'agua', 'gas', 'internet']
    }
    
    for transacao in transacoes:
        descricao_lower = transacao.get('descricao', '').lower()
        
        # Busca categoria baseada na descrição
        for categoria, palavras_chave in mapeamento_categorias.items():
            if any(palavra in descricao_lower for palavra in palavras_chave):
                # Busca a categoria no banco
                categoria_obj = db.query(Categoria).filter(
                    Categoria.nome.ilike(f'%{categoria}%')
                ).first()
                
                if categoria_obj:
                    transacao['id_categoria'] = categoria_obj.id
                    break
    
    return transacoes

def preparar_dados_para_grafico(lancamentos: List[Lancamento], agrupar_por: str):
    """
    Prepara dados dos lançamentos para geração de gráficos.
    
    Returns:
        tuple: (DataFrame preparado, bool se tem dados suficientes)
    """
    from datetime import datetime
    
    if not lancamentos:
        return pd.DataFrame(), False
    
    # Converter lançamentos para DataFrame
    dados = []
    for lancamento in lancamentos:
        # CORREÇÃO: Extrair nome da categoria corretamente
        if hasattr(lancamento, 'categoria') and lancamento.categoria:
            categoria_str = lancamento.categoria.nome
        else:
            categoria_str = 'Sem Categoria'
        
        # forma_pagamento já é string no modelo Lancamento
        forma_pagamento_str = lancamento.forma_pagamento or 'Não informado'
        
        dados.append({
            'data': lancamento.data_transacao,
            'valor': float(lancamento.valor),
            'descricao': lancamento.descricao or 'Sem descrição',
            'tipo': 'Receita' if lancamento.valor > 0 else 'Despesa',
            'mes': lancamento.data_transacao.strftime('%Y-%m'),
            'ano': lancamento.data_transacao.year,
            'categoria': categoria_str,
            'forma_pagamento': forma_pagamento_str
        })
    
    df = pd.DataFrame(dados)
    
    if len(df) == 0:
        return df, False
    
    # Processar dados baseado no tipo de agrupamento
    if agrupar_por == 'categoria':
        # Agrupar por categoria e somar valores absolutos (receitas + despesas)
        df_agrupado = df.groupby('categoria')['valor'].apply(lambda x: x.abs().sum()).reset_index()
        df_agrupado = df_agrupado[df_agrupado['valor'] > 0]  # Qualquer valor > 0
        df_agrupado['grupo'] = df_agrupado['categoria']
        
    elif agrupar_por == 'forma_pagamento':
        # Agrupar por forma de pagamento (receitas + despesas)
        df_agrupado = df.groupby('forma_pagamento')['valor'].apply(lambda x: x.abs().sum()).reset_index()
        df_agrupado = df_agrupado[df_agrupado['valor'] > 0]  # Qualquer valor > 0
        df_agrupado['grupo'] = df_agrupado['forma_pagamento']
        
    elif agrupar_por == 'data':
        # Agrupar por data para evolução temporal
        df['Saldo Acumulado'] = df['valor'].cumsum()
        df_agrupado = df.copy()
        df_agrupado['grupo'] = df_agrupado['data'].dt.strftime('%Y-%m-%d')
        
    elif agrupar_por == 'mes':
        # Agrupar por mês
        df_agrupado = df.groupby('mes')['valor'].sum().reset_index()
        df_agrupado['grupo'] = df_agrupado['mes']
        
    else:
        # Fallback - agrupar por tipo
        df_agrupado = df.groupby('tipo')['valor'].apply(lambda x: x.abs().sum()).reset_index()
        df_agrupado['grupo'] = df_agrupado['tipo']
    
    # Verificar se temos dados suficientes
    tem_dados_suficientes = len(df_agrupado) >= 1 and df_agrupado['valor'].sum() > 0
    
    return df_agrupado, tem_dados_suficientes

def gerar_grafico_dinamico(lancamentos: List[Lancamento], tipo_grafico: str, agrupar_por: str) -> Optional[io.BytesIO]:
    """
    Gera gráficos financeiros dinâmicos com um design aprimorado e profissional.
    """
    try:
        # --- ESTILO GLOBAL PARA TODOS OS GRÁFICOS ---
        plt.style.use('seaborn-v0_8-darkgrid')
        plt.rcParams.update({
            'font.family': 'sans-serif',
            'font.sans-serif': ['Arial', 'Helvetica', 'DejaVu Sans'], # Fallback de fontes
            'axes.labelcolor': '#333333',
            'xtick.color': '#333333',
            'ytick.color': '#333333',
            'axes.titlecolor': '#1a2b4c',
            'axes.edgecolor': '#cccccc',
            'axes.titleweight': 'bold',
            'axes.titlesize': 18,
            'figure.dpi': 120
        })

        df, tem_dados_suficientes = preparar_dados_para_grafico(lancamentos, agrupar_por)
        if not tem_dados_suficientes:
            return None
            
        fig, ax = plt.subplots(figsize=(12, 7))

        # --- GRÁFICOS DE CATEGORIA E FORMA DE PAGAMENTO ---
        if agrupar_por in ['categoria', 'forma_pagamento']:
            
            # GRÁFICO DE PIZZA (AGORA DONUT CHART)
            if tipo_grafico == 'pizza':
                nome_agrupamento = 'Categoria' if agrupar_por == 'categoria' else 'Forma de Pagamento'
                ax.set_title(f'Distribuição de Valores por {nome_agrupamento}', pad=20, fontsize=16, weight='bold')
                
                # Paleta de cores vibrante e profissional
                colors = plt.cm.Set3(np.linspace(0, 1, len(df['grupo'])))
                
                # Explode as fatias para melhor visualização (maior fatia com destaque)
                valores_norm = df['valor'] / df['valor'].sum()
                explode = [0.08 if v == valores_norm.max() else 0.03 for v in valores_norm]
                
                wedges, texts, autotexts = ax.pie(
                    df['valor'], 
                    autopct='%1.1f%%', 
                    startangle=90, 
                    colors=colors, 
                    pctdistance=0.82,
                    explode=explode,
                    wedgeprops={'edgecolor': 'white', 'linewidth': 3, 'antialiased': True},
                    textprops={'fontsize': 11, 'weight': 'bold'}
                )
                
                # Melhora visibilidade dos percentuais
                for autotext in autotexts:
                    autotext.set_color('white')
                    autotext.set_fontsize(12)
                    autotext.set_weight('bold')
                    autotext.set_bbox(dict(boxstyle='round,pad=0.3', facecolor='black', alpha=0.3))
                
                # Desenha o círculo no centro para criar o efeito DONUT
                centre_circle = plt.Circle((0,0), 0.68, fc='white', linewidth=0)
                fig.gca().add_artist(centre_circle)
                
                # Total no centro do donut
                total = df['valor'].sum()
                ax.text(0, 0, f'Total\nR$ {total:,.2f}'.replace(',', '.'), 
                       ha='center', va='center', fontsize=14, weight='bold', color='#2c3e50')
                
                # Legenda limpa e organizada com valores
                legend_labels = [f"{label}: R$ {valor:,.2f}".replace(',', '.') for label, valor in zip(df['grupo'], df['valor'])]
                ax.legend(wedges, legend_labels, title=nome_agrupamento, title_fontsize=12,
                         loc="center left", bbox_to_anchor=(1, 0, 0.5, 1), fontsize=10,
                         frameon=True, fancybox=True, shadow=True)
                ax.axis('equal')

            # GRÁFICO DE BARRAS HORIZONTAIS
            elif tipo_grafico == 'barra_h':
                nome_agrupamento = 'Categoria' if agrupar_por == 'categoria' else 'Forma de Pagamento'
                ax.set_title(f'Gastos por {nome_agrupamento}', pad=20, fontsize=16, weight='bold')
                df = df.sort_values('valor', ascending=True) # Ordena do menor para o maior
                
                # Paleta de cores gradiente moderna
                colors = plt.cm.viridis(np.linspace(0.2, 0.9, len(df)))
                bars = ax.barh(df['grupo'], df['valor'], color=colors, edgecolor='white', linewidth=1.5, height=0.7)
                
                ax.set_xlabel('Valor Gasto (R$)', fontsize=13, weight='bold')
                ax.set_ylabel('')
                ax.grid(axis='x', linestyle='--', alpha=0.3) # Grade vertical sutil
                ax.set_axisbelow(True)
                
                # Rótulos de valor formatados
                max_valor = df['valor'].max()
                for i, (bar, valor) in enumerate(zip(bars, df['valor'])):
                    width = bar.get_width()
                    # Posiciona rótulo dentro da barra se for grande, fora se for pequena
                    if valor > max_valor * 0.15:
                        ax.text(width * 0.95, bar.get_y() + bar.get_height()/2,
                               f'R$ {width:,.2f}'.replace(',', '.'),
                               va='center', ha='right', fontsize=11, weight='bold', color='white')
                    else:
                        ax.text(width + (max_valor * 0.02), bar.get_y() + bar.get_height()/2,
                               f'R$ {width:,.2f}'.replace(',', '.'),
                               va='center', ha='left', fontsize=11, weight='bold', color='#2c3e50')

        # --- GRÁFICOS BASEADOS EM DATA ---
        elif agrupar_por in ['data', 'fluxo_caixa', 'projecao']:
            
            # GRÁFICO DE EVOLUÇÃO DO SALDO (LINHA)
            if agrupar_por == 'data':
                if len(df) < 2: return None # Precisa de pelo menos 2 pontos
                ax.set_title('Evolução do Saldo Financeiro', pad=20)
                
                # Verificar se temos a coluna 'Saldo Acumulado' (preparada em preparar_dados_para_grafico)
                if 'Saldo Acumulado' not in df.columns:
                    logger.error("Coluna 'Saldo Acumulado' não encontrada no DataFrame")
                    return None
                
                # Converter data para datetime se necessário
                if not pd.api.types.is_datetime64_any_dtype(df['data']):
                    df['data'] = pd.to_datetime(df['data'])
                
                df = df.sort_values('data')
                
                # Decidir se suaviza ou não baseado no número de pontos
                if len(df) >= 5:
                    # Suavização da linha (apenas se tiver dados suficientes)
                    try:
                        x_smooth = np.linspace(df['data'].astype(np.int64).min(), df['data'].astype(np.int64).max(), 300)
                        x_smooth_dt = pd.to_datetime(x_smooth)
                        spl = make_interp_spline(df['data'].astype(np.int64), df['Saldo Acumulado'], k=min(2, len(df)-1))
                        y_smooth = spl(x_smooth)
                        
                        ax.plot(x_smooth_dt, y_smooth, label='Saldo Acumulado', color='#3498db', linewidth=3)
                        ax.fill_between(x_smooth_dt, y_smooth, alpha=0.15, color='#3498db')
                    except Exception as e:
                        logger.warning(f"Erro na suavização, usando linha simples: {e}")
                        ax.plot(df['data'], df['Saldo Acumulado'], label='Saldo Acumulado', color='#3498db', linewidth=3, marker='o')
                        ax.fill_between(df['data'], df['Saldo Acumulado'], alpha=0.15, color='#3498db')
                else:
                    # Linha simples para poucos pontos
                    ax.plot(df['data'], df['Saldo Acumulado'], label='Saldo Acumulado', color='#3498db', linewidth=3, marker='o', markersize=8)
                    ax.fill_between(df['data'], df['Saldo Acumulado'], alpha=0.15, color='#3498db')
                
                # Destaque do pico máximo e mínimo
                pico_max = df.loc[df['Saldo Acumulado'].idxmax()]
                pico_min = df.loc[df['Saldo Acumulado'].idxmin()]
                
                ax.scatter(pico_max['data'], pico_max['Saldo Acumulado'], color='#2ecc71', s=180, zorder=5, label='Maior Saldo', edgecolor='white', linewidth=2)
                ax.scatter(pico_min['data'], pico_min['Saldo Acumulado'], color='#e74c3c', s=180, zorder=5, label='Menor Saldo', edgecolor='white', linewidth=2)
                
                # Anotações nos picos (com posicionamento dinâmico)
                offset_max = abs(pico_max['Saldo Acumulado']) * 0.05
                offset_min = abs(pico_min['Saldo Acumulado']) * 0.05
                ax.text(pico_max['data'], pico_max['Saldo Acumulado'] + offset_max, 
                       f'R$ {pico_max["Saldo Acumulado"]:.2f}', 
                       ha='center', fontsize=11, weight='bold', color='#2ecc71', 
                       bbox=dict(boxstyle='round,pad=0.4', fc='white', alpha=0.8, edgecolor='#2ecc71'))
                ax.text(pico_min['data'], pico_min['Saldo Acumulado'] - offset_min, 
                       f'R$ {pico_min["Saldo Acumulado"]:.2f}', 
                       ha='center', fontsize=11, weight='bold', color='#e74c3c',
                       bbox=dict(boxstyle='round,pad=0.4', fc='white', alpha=0.8, edgecolor='#e74c3c'))

                ax.legend(fontsize=11, loc='best')
                ax.axhline(0, color='gray', linewidth=0.8, linestyle='--', alpha=0.5)

            # GRÁFICO DE PROJEÇÃO (BARRAS HORIZONTAIS)
            elif agrupar_por == 'projecao':
                today = datetime.now()
                start_of_month = today.replace(day=1, hour=0, minute=0, second=0)
                
                # Filtrar apenas despesas do mês atual
                despesas_mes_atual = [
                    l for l in lancamentos 
                    if l.data_transacao >= start_of_month 
                    and l.data_transacao <= today
                    and l.tipo == 'Despesa'
                ]
                
                if not despesas_mes_atual:
                    logger.info("Nenhuma despesa encontrada no mês atual para projeção")
                    return None
                
                # Calcular total de gastos até hoje
                total_gasto = sum(abs(float(l.valor)) for l in despesas_mes_atual)
                
                if total_gasto == 0:
                    logger.info("Total de gastos é zero, sem projeção possível")
                    return None
                
                # Calcular projeção
                dias_no_mes = (today.replace(month=today.month % 12 + 1 if today.month != 12 else 1, day=1, year=today.year if today.month != 12 else today.year + 1) - timedelta(days=1)).day
                dias_passados = today.day
                gasto_medio_diario = total_gasto / dias_passados
                gasto_projetado = gasto_medio_diario * dias_no_mes
                
                # Nome do mês em português
                meses_pt = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 
                           'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
                mes_nome = meses_pt[today.month - 1]
                
                ax.set_title(f'Projeção de Gastos para {mes_nome}/{today.year}', pad=20, fontsize=16)
                
                # Dados para o gráfico
                labels = ['💰 Gasto até Hoje', '📊 Projeção Mensal']
                valores = [total_gasto, gasto_projetado]
                cores = ['#3498db', '#e74c3c']

                bars = ax.barh(labels, valores, color=cores, edgecolor='white', linewidth=2, height=0.6)
                ax.invert_yaxis() # Gasto atual em cima
                
                ax.set_xlabel('Valor (R$)', fontsize=13, weight='bold')
                ax.grid(axis='x', alpha=0.3, linestyle='--')
                
                # Rótulos de valor
                for i, (bar, valor) in enumerate(zip(bars, valores)):
                    width = bar.get_width()
                    ax.text(width + (gasto_projetado * 0.02), bar.get_y() + bar.get_height()/2,
                           f'R$ {valor:,.2f}'.replace(',', '.'),
                           va='center', ha='left', fontsize=12, weight='bold', color=cores[i])
                
                # Informações adicionais
                dias_restantes = dias_no_mes - dias_passados
                gasto_restante = gasto_projetado - total_gasto
                
                info_text = (
                    f"📅 Dia {dias_passados}/{dias_no_mes} ({dias_restantes} dias restantes)\n"
                    f"📈 Média diária: R$ {gasto_medio_diario:.2f}\n"
                    f"💸 Estimativa restante: R$ {gasto_restante:.2f}"
                )
                
                ax.text(0.02, 0.98, info_text,
                       transform=ax.transAxes, fontsize=10,
                       verticalalignment='top',
                       bbox=dict(boxstyle='round,pad=0.6', fc='lightyellow', alpha=0.8, edgecolor='gray'))

            # GRÁFICO DE FLUXO DE CAIXA
            elif agrupar_por == 'fluxo_caixa':
                # Preparar dados para fluxo de caixa
                dados_fluxo = []
                for l in lancamentos:
                    # CORREÇÃO: Tipos corretos são 'Receita' e 'Despesa' (não 'Entrada'/'Saída')
                    entrada = float(l.valor) if l.tipo == 'Receita' else 0
                    saida = abs(float(l.valor)) if l.tipo == 'Despesa' else 0
                    dados_fluxo.append({
                        'data': l.data_transacao,
                        'entrada': entrada,
                        'saida': saida
                    })
                
                df_fluxo = pd.DataFrame(dados_fluxo)
                df_fluxo['data'] = pd.to_datetime(df_fluxo['data'])
                
                # Agrupar por data
                df_agrupado = df_fluxo.groupby(df_fluxo['data'].dt.date).agg({
                    'entrada': 'sum',
                    'saida': 'sum'
                }).reset_index()
                df_agrupado['data'] = pd.to_datetime(df_agrupado['data'])
                df_agrupado = df_agrupado.sort_values('data')
                
                if df_agrupado['entrada'].sum() == 0 and df_agrupado['saida'].sum() == 0:
                    logger.info("Sem dados de fluxo de caixa para exibir")
                    return None
                
                ax.set_title('Fluxo de Caixa (Receitas vs. Despesas)', pad=20, fontsize=16, weight='bold')
                
                # Barras com cores modernas e bordas
                width_days = (df_agrupado['data'].max() - df_agrupado['data'].min()).days
                bar_width = max(0.8, min(3, width_days / len(df_agrupado) * 0.7))
                
                ax.bar(df_agrupado['data'], df_agrupado['entrada'], 
                      color='#27ae60', label='💰 Receitas', 
                      width=bar_width, edgecolor='white', linewidth=1.5, alpha=0.9)
                ax.bar(df_agrupado['data'], -df_agrupado['saida'], 
                      color='#e74c3c', label='💸 Despesas', 
                      width=bar_width, edgecolor='white', linewidth=1.5, alpha=0.9)
                
                # Linha zero de referência
                ax.axhline(0, color='#2c3e50', linewidth=1.5, linestyle='-', alpha=0.7, zorder=0)
                
                # Estatísticas no gráfico
                total_receitas = df_agrupado['entrada'].sum()
                total_despesas = df_agrupado['saida'].sum()
                saldo_liquido = total_receitas - total_despesas
                
                stats_text = (
                    f"💰 Total Receitas: R$ {total_receitas:,.2f}\n"
                    f"💸 Total Despesas: R$ {total_despesas:,.2f}\n"
                    f"{'📈' if saldo_liquido >= 0 else '📉'} Saldo Líquido: R$ {saldo_liquido:,.2f}"
                ).replace(',', '.')
                
                ax.text(0.02, 0.98, stats_text,
                       transform=ax.transAxes, fontsize=10,
                       verticalalignment='top',
                       bbox=dict(boxstyle='round,pad=0.6', fc='lightyellow', alpha=0.85, edgecolor='gray'))
                
                ax.legend(fontsize=11, loc='lower right', frameon=True, fancybox=True, shadow=True)
                ax.grid(axis='y', linestyle='--', alpha=0.3)
            
            ax.set_ylabel('Valor (R$)', fontsize=12)
            fig.autofmt_xdate(rotation=30)
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))

        else:
            return None
        
        plt.tight_layout(pad=1.5)
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', bbox_inches='tight')
        buffer.seek(0)
        plt.close(fig) # Garante que a figura seja fechada para liberar memória
        return buffer
    except Exception as e:
        logger.error(f"Erro CRÍTICO ao gerar gráfico: {e}", exc_info=True)
        plt.close('all') # Fecha todas as figuras em caso de erro
        return None
    
# --- SISTEMA DE INSIGHTS PROATIVOS ---
def _gerar_insights_automaticos(lancamentos: List[Lancamento]) -> List[Dict[str, Any]]:
    """Gera insights automáticos baseados nos padrões dos lançamentos"""
    if not lancamentos:
        return []
    
    insights = []
    agora = datetime.now()
    
    # Análise de gastos dos últimos 30 dias
    ultimos_30_dias = [l for l in lancamentos if (agora - l.data_transacao).days <= 30]
    
    if ultimos_30_dias:
        # Insight 1: Maior categoria de gasto
        gastos_por_categoria = {}
        for l in ultimos_30_dias:
            if l.tipo == 'Despesa' and l.categoria:
                cat = l.categoria.nome
                gastos_por_categoria[cat] = gastos_por_categoria.get(cat, 0) + float(l.valor)
        
        if gastos_por_categoria:
            maior_categoria = max(gastos_por_categoria.items(), key=lambda x: x[1])
            insights.append({
                "tipo": "categoria_dominante",
                "titulo": f"🔍 Categoria que mais consome seu orçamento",
                "descricao": f"Nos últimos 30 dias, '{maior_categoria[0]}' representa R$ {maior_categoria[1]:.2f} dos seus gastos",
                "valor": maior_categoria[1],
                "categoria": maior_categoria[0]
            })
        
        # Insight 2: Frequência de transações
        frequencia_semanal = len(ultimos_30_dias) / 4.3  # 30 dias ÷ semanas
        if frequencia_semanal > 15:
            insights.append({
                "tipo": "alta_frequencia",
                "titulo": "⚡ Alta atividade financeira detectada",
                "descricao": f"Você fez {len(ultimos_30_dias)} transações em 30 dias ({frequencia_semanal:.1f} por semana)",
                "valor": len(ultimos_30_dias)
            })
        
        # Insight 3: Padrão de fins de semana
        gastos_weekend = [l for l in ultimos_30_dias if l.data_transacao.weekday() >= 5 and l.tipo == 'Despesa']
        total_weekend = sum(float(l.valor) for l in gastos_weekend)
        total_geral = sum(float(l.valor) for l in ultimos_30_dias if l.tipo == 'Despesa')
        
        if total_geral > 0:
            percentual_weekend = (total_weekend / total_geral) * 100
            if percentual_weekend > 35:
                insights.append({
                    "tipo": "gastos_weekend",
                    "titulo": "🎉 Perfil de gastos: fins de semana ativos",
                    "descricao": f"{percentual_weekend:.1f}% dos seus gastos acontecem nos fins de semana",
                    "valor": percentual_weekend
                })
    
    return insights

def _detectar_padroes_comportamentais(lancamentos: List[Lancamento]) -> List[Dict[str, Any]]:
    """Detecta padrões comportamentais avançados"""
    if not lancamentos:
        return []
    
    padroes = []
    
    # Agrupa por mês para análise temporal
    gastos_mensais = {}
    for l in lancamentos:
        if l.tipo == 'Despesa':
            mes_ano = l.data_transacao.strftime('%Y-%m')
            gastos_mensais[mes_ano] = gastos_mensais.get(mes_ano, 0) + float(l.valor)
    
    if len(gastos_mensais) >= 2:
        valores = list(gastos_mensais.values())
        
        # Padrão 1: Tendência de crescimento/decrescimento
        if len(valores) >= 3:
            ultimos_3 = valores[-3:]
            if all(ultimos_3[i] > ultimos_3[i-1] for i in range(1, len(ultimos_3))):
                padroes.append({
                    "tipo": "tendencia_crescimento",
                    "descricao": "Gastos mensais em tendência de crescimento",
                    "detalhes": f"Últimos 3 meses: {[f'R$ {v:.2f}' for v in ultimos_3]}"
                })
            elif all(ultimos_3[i] < ultimos_3[i-1] for i in range(1, len(ultimos_3))):
                padroes.append({
                    "tipo": "tendencia_economia",
                    "descricao": "Gastos mensais em tendência de redução - Parabéns! 📉✅",
                    "detalhes": f"Últimos 3 meses: {[f'R$ {v:.2f}' for v in ultimos_3]}"
                })
        
        # Padrão 2: Variabilidade dos gastos
        if len(valores) >= 2:
            media = sum(valores) / len(valores)
            desvio = sum((v - media) ** 2 for v in valores) / len(valores)
            coef_variacao = (desvio ** 0.5) / media if media > 0 else 0
            
            if coef_variacao > 0.3:
                padroes.append({
                    "tipo": "alta_variabilidade",
                    "descricao": "Gastos mensais com alta variabilidade",
                    "detalhes": f"Coeficiente de variação: {coef_variacao:.2f} (>0.3 indica irregularidade)"
                })
            elif coef_variacao < 0.15:
                padroes.append({
                    "tipo": "gastos_estables",
                    "descricao": "Padrão de gastos muito estável - Excelente controle! 🎯",
                    "detalhes": f"Variação baixa entre os meses ({coef_variacao:.2f})"
                })
    
    return padroes

async def _obter_dados_mercado_financeiro():
    """
    Obtém dados básicos do mercado financeiro.
    Implementação simplificada para evitar erros.
    """
    return {
        'selic': 'N/A',
        'ipca': 'N/A',
        'dolar': 'N/A',
        'ibovespa': 'N/A',
        'status': 'offline'
    }

async def _obter_dados_economicos_contexto():
    """
    Obtém dados econômicos de contexto.
    Implementação simplificada para evitar erros.
    """
    return {
        'inflacao_mensal': 'N/A',
        'pib_crescimento': 'N/A',
        'desemprego': 'N/A',
        'status': 'offline'
    }

async def _classificar_situacao_comparativa(economia_mensal: float, gastos_mensais: float):
    """
    Classifica a situação financeira do usuário comparativamente.
    """
    if economia_mensal > gastos_mensais * 0.3:
        return "🟢 Excelente - Economia acima de 30% dos gastos"
    elif economia_mensal > gastos_mensais * 0.2:
        return "🟡 Boa - Economia entre 20-30% dos gastos"
    elif economia_mensal > gastos_mensais * 0.1:
        return "🟠 Regular - Economia entre 10-20% dos gastos"
    else:
        return "🔴 Atenção - Economia abaixo de 10% dos gastos"

def _obter_estatisticas_cache():
    """
    Obtém estatísticas básicas do cache.
    Implementação simplificada para evitar erros.
    """
    return {
        'cache_size': 0,
        'cache_hits': 0,
        'cache_misses': 0,
        'last_cleanup': datetime.now().isoformat(),
        'status': 'active'
    }

async def preparar_contexto_financeiro_completo(db: Session, usuario: Usuario) -> str:
    """
    Coleta e formata um resumo completo do ecossistema financeiro do usuário.
    VERSÃO 6.0 - Com OPEN FINANCE integrado + cache inteligente + análise comportamental.
    
    Agora busca dados de:
    1. Lançamentos manuais (tabela lancamentos)
    2. 🏦 Transações bancárias reais (tabela bank_transactions via Open Finance)
    """
    # Limpeza automática de cache
    _limpar_cache_expirado()
    
    # Busca lançamentos manuais
    lancamentos = db.query(Lancamento).filter(Lancamento.id_usuario == usuario.id).options(
        joinedload(Lancamento.categoria)
    ).order_by(Lancamento.data_transacao.asc()).all()
    
    # 🏦 NOVO: Busca transações bancárias do Open Finance
    transacoes_bancarias = _buscar_transacoes_open_finance(db, usuario.id)
    
    # 🏦 Mescla os dois conjuntos de dados
    total_transacoes = len(lancamentos) + len(transacoes_bancarias)
    
    if total_transacoes == 0:
        return json.dumps({"resumo": "Nenhum dado financeiro encontrado."}, indent=2, ensure_ascii=False)

    # Gera chave de cache baseada na data do último lançamento (mais estável)
    ultima_data = lancamentos[-1].data_transacao.strftime('%Y-%m-%d')
    chave_cache = _gerar_chave_cache(
        usuario.id, 
        'contexto_completo',
        ultima_data=ultima_data,
        total_lancamentos=len(lancamentos)
    )
    
    # 🧠 Cache inteligente com invalidação por hash
    dados_cache = _obter_do_cache(chave_cache, db, usuario.id)
    if dados_cache:
        logger.info(f"✅ Contexto financeiro obtido do CACHE para usuário {usuario.id}")
        return dados_cache
    
    logger.info(f"🔄 Cache MISS ou INVALIDADO - recalculando contexto para usuário {usuario.id}")

    # Análise comportamental completa
    analise_comportamental = analisar_comportamento_financeiro(lancamentos)
    
    # Dados de mercado e econômicos
    dados_mercado = await _obter_dados_mercado_financeiro()
    dados_economicos = await _obter_dados_economicos_contexto()
    
    # Classificação comparativa
    economia_mensal = analise_comportamental.get('economia_media_mensal', 0)
    gastos_mensais = abs(analise_comportamental.get('total_despesas_90d', 0)) / 3  # Aproximação mensal
    situacao_comparativa = await _classificar_situacao_comparativa(economia_mensal, gastos_mensais)
    
    data_minima = lancamentos[0].data_transacao.strftime('%d/%m/%Y')
    data_maxima = lancamentos[-1].data_transacao.strftime('%d/%m/%Y')
    resumo_mensal = {}
    for l in lancamentos:
        mes_ano = l.data_transacao.strftime('%Y-%m')
        if mes_ano not in resumo_mensal:
            resumo_mensal[mes_ano] = {'receitas': 0.0, 'despesas': 0.0}
        if l.tipo == 'Receita':
            resumo_mensal[mes_ano]['receitas'] += float(l.valor)
        else:
            resumo_mensal[mes_ano]['despesas'] += float(l.valor)
    for mes, valores in resumo_mensal.items():
        valores['receitas'] = f"R$ {valores['receitas']:.2f}"
        valores['despesas'] = f"R$ {valores['despesas']:.2f}"

    contas_db = db.query(Conta).filter(Conta.id_usuario == usuario.id).all()
    metas_db = db.query(Objetivo).filter(Objetivo.id_usuario == usuario.id).all()
    metas_financeiras = [
        {"descricao": o.descricao, "valor_meta": f"R$ {o.valor_meta:.2f}", "valor_atual": f"R$ {o.valor_atual:.2f}"}
        for o in metas_db
    ]
    
    # 🏦 Adiciona transações bancárias ao resumo mensal
    for transacao in transacoes_bancarias:
        try:
            data_str = transacao.get('data')
            if data_str:
                data_obj = datetime.strptime(data_str, '%Y-%m-%d')
                mes_ano = data_obj.strftime('%Y-%m')
                
                if mes_ano not in resumo_mensal:
                    resumo_mensal[mes_ano] = {'receitas': 0.0, 'despesas': 0.0}
                
                valor = float(transacao.get('valor', 0))
                if valor > 0:
                    # Converte string de volta para float se necessário
                    if isinstance(resumo_mensal[mes_ano]['receitas'], str):
                        resumo_mensal[mes_ano]['receitas'] = float(resumo_mensal[mes_ano]['receitas'].replace('R$ ', '').replace(',', '.'))
                    resumo_mensal[mes_ano]['receitas'] += valor
                else:
                    if isinstance(resumo_mensal[mes_ano]['despesas'], str):
                        resumo_mensal[mes_ano]['despesas'] = float(resumo_mensal[mes_ano]['despesas'].replace('R$ ', '').replace(',', '.'))
                    resumo_mensal[mes_ano]['despesas'] += abs(valor)
        except Exception as e:
            logger.warning(f"Erro ao processar transação bancária: {e}")
    
    # Formata valores monetários no resumo mensal
    for mes, valores in resumo_mensal.items():
        if isinstance(valores['receitas'], float):
            valores['receitas'] = f"R$ {valores['receitas']:.2f}"
        if isinstance(valores['despesas'], float):
            valores['despesas'] = f"R$ {valores['despesas']:.2f}"
    
    # 🏦 Mescla lançamentos manuais + transações bancárias
    todos_dados_financeiros = [
        {
            "data": l.data_transacao.strftime('%Y-%m-%d'),
            "descricao": l.descricao,
            "valor": float(l.valor),
            "tipo": l.tipo,
            "categoria": l.categoria.nome if l.categoria else "Sem Categoria",
            "conta": l.forma_pagamento,
            "dia_semana": l.data_transacao.weekday(),
            "hora": l.data_transacao.hour,
            "fonte": "manual"
        } for l in lancamentos
    ] + [
        {
            "data": t['data'],
            "descricao": t['descricao'],
            "valor": t['valor'],
            "tipo": t['tipo'],
            "categoria": t['categoria'],
            "conta": t['conta'],
            "tipo_conta": t['tipo_conta'],
            "banco": t['banco'],
            "dia_semana": datetime.strptime(t['data'], '%Y-%m-%d').weekday() if t['data'] else None,
            "fonte": "open_finance"  # 🏦 Identifica origem
        } for t in transacoes_bancarias
    ]
    
    # Ordena tudo por data
    todos_dados_financeiros.sort(key=lambda x: x['data'], reverse=True)
    
    # Contexto completo com OPEN FINANCE integrado
    contexto_completo = {
        "informacoes_gerais": {
            "data_atual": datetime.now().strftime('%d/%m/%Y'),
            "periodo_disponivel": f"{data_minima} a {data_maxima}",
            "contas_cadastradas": [c.nome for c in contas_db],
            "metas_financeiras": metas_financeiras,
            "insights_automaticos": _gerar_insights_automaticos(lancamentos),
            "padroes_detectados": _detectar_padroes_comportamentais(lancamentos),
            "estatisticas_cache": _obter_estatisticas_cache(),
            # 🏦 NOVO: Estatísticas Open Finance
            "open_finance": {
                "ativo": len(transacoes_bancarias) > 0,
                "total_transacoes_bancarias": len(transacoes_bancarias),
                "total_lancamentos_manuais": len(lancamentos),
                "bancos_conectados": list(set([t['banco'] for t in transacoes_bancarias]))
            }
        },
        "analise_comportamental_avancada": analise_comportamental,
        "contexto_economico": {
            "dados_mercado": dados_mercado,
            "indicadores_economicos": dados_economicos,
            "situacao_comparativa": situacao_comparativa
        },
        "resumo_por_mes": resumo_mensal,
        # 🏦 DADOS MESCLADOS (manual + bancário)
        "todos_lancamentos": todos_dados_financeiros
    }

    resultado = json.dumps(contexto_completo, indent=2, ensure_ascii=False)
    
    # 🧠 Salva no cache com hash de transações
    _salvar_no_cache(chave_cache, resultado, db, usuario.id)
    logger.info(f"💾 Contexto salvo no cache para usuário {usuario.id}")
    logger.info(f"✅ Contexto financeiro v6.0 (com Open Finance) calculado para usuário {usuario.id}")
    logger.info(f"📊 Total: {len(lancamentos)} manuais + {len(transacoes_bancarias)} bancárias = {total_transacoes} transações")
    
    return resultado

# --- CACHE ESPECÍFICO PARA RESPOSTAS DA IA ---
_cache_respostas_ia = {}  # Cache para respostas da IA
_cache_respostas_tempo = {}  # Timestamps das respostas

def _gerar_chave_resposta_ia(user_id: int, pergunta: str, hash_dados: str) -> str:
    """
    Gera chave de cache baseada na pergunta e no hash dos dados financeiros
    Isso garante que respostas idênticas sejam cacheadas
    """
    chave_base = f"ia_{user_id}_{pergunta.lower().strip()}_{hash_dados}"
    return hashlib.md5(chave_base.encode()).hexdigest()

def _obter_resposta_ia_cache(chave: str) -> Optional[str]:
    """
    Obtém resposta da IA do cache se válida.
    Limpeza automática de entradas antigas.
    """
    # Limpeza preventiva (1% de chance a cada chamada)
    import random
    if random.random() < 0.01:
        _limpar_cache_ia_expirado()
    
    if chave in _cache_respostas_tempo:
        tempo_cache = _cache_respostas_tempo[chave]
        tempo_atual = time.time()
        if (tempo_atual - tempo_cache) < CACHE_TTL:
            logger.info(f"✨ Cache HIT: {chave[:16]}...")
            return _cache_respostas_ia.get(chave)
        else:
            logger.info(f"⏰ Cache EXPIRED: {chave[:16]}...")
    return None

def _salvar_resposta_ia_cache(chave: str, resposta: str) -> None:
    """Salva resposta da IA no cache com controle de tamanho"""
    # Limita o tamanho do cache (máximo 100 entradas)
    if len(_cache_respostas_ia) >= 100:
        # Remove as 20 entradas mais antigas
        chaves_ordenadas = sorted(_cache_respostas_tempo.items(), key=lambda x: x[1])
        for chave_antiga, _ in chaves_ordenadas[:20]:
            _cache_respostas_ia.pop(chave_antiga, None)
            _cache_respostas_tempo.pop(chave_antiga, None)
        logger.info(f"🧹 Cache: Removidas 20 entradas antigas (limite atingido)")
    
    _cache_respostas_ia[chave] = resposta
    _cache_respostas_tempo[chave] = time.time()
    logger.info(f"💾 Cache SAVE: {chave[:16]}... (total: {len(_cache_respostas_ia)} entradas)")

def _gerar_hash_dados_financeiros(contexto_financeiro: str) -> str:
    """Gera hash dos dados financeiros para detectar mudanças"""
    return hashlib.md5(contexto_financeiro.encode()).hexdigest()[:16]

def _limpar_cache_expirado():
    """Remove entradas de cache expiradas do cache financeiro."""
    tempo_atual = datetime.now().timestamp()
    expirados = [chave for chave, t in _cache_tempo.items() if (tempo_atual - t) >= CACHE_TTL]
    for chave in expirados:
        _cache_financeiro.pop(chave, None)
        _cache_tempo.pop(chave, None)

def _limpar_cache_ia_expirado():
    """Remove entradas de cache de IA expiradas."""
    tempo_atual = time.time()
    expirados = [
        chave for chave, t in _cache_respostas_tempo.items() 
        if (tempo_atual - t) >= CACHE_TTL
    ]
    for chave in expirados:
        _cache_respostas_ia.pop(chave, None)
        _cache_respostas_tempo.pop(chave, None)
    
    if expirados:
        logger.info(f"🧹 Cache IA: Removidas {len(expirados)} entradas expiradas")

# ==================== 🏦 INTEGRAÇÃO OPEN FINANCE ====================

def _buscar_transacoes_open_finance(db: Session, user_id: int) -> List[Dict]:
    """
    Busca transações bancárias reais do Open Finance (últimos 90 dias).
    
    Retorna lista de dicionários no mesmo formato dos lançamentos manuais
    para facilitar mesclagem e análise.
    
    Args:
        db: Sessão do banco de dados
        user_id: ID do usuário (Telegram ID)
    
    Returns:
        Lista de transações bancárias formatadas
    """
    try:
        # Query com JOIN triplo: transactions -> accounts -> connections
        query = text("""
            SELECT 
                bt.transaction_id,
                bt.description,
                bt.amount,
                bt.date,
                bt.type,
                bt.category,
                bt.merchant_name,
                ba.account_name,
                ba.account_type,
                bc.connector_id
            FROM bank_transactions bt
            INNER JOIN bank_accounts ba ON bt.account_id = ba.id
            INNER JOIN bank_connections bc ON ba.connection_id = bc.id
            WHERE bc.user_id = :user_id
                AND bc.status = 'UPDATED'
                AND bt.date >= CURRENT_DATE - INTERVAL '90 days'
            ORDER BY bt.date DESC
        """)
        
        resultado = db.execute(query, {"user_id": user_id})
        transacoes = []
        
        for row in resultado:
            # Formata no mesmo padrão dos lançamentos manuais
            transacao = {
                "id": row[0],  # transaction_id
                "data": row[3].strftime('%Y-%m-%d') if row[3] else None,
                "descricao": row[1] or row[6] or "Transação bancária",  # description ou merchant_name
                "valor": float(row[2]) if row[2] else 0.0,
                "tipo": "Receita" if row[2] > 0 else "Despesa",
                "categoria": row[5] or "Open Finance",
                "conta": row[7] or "Banco conectado",  # account_name
                "tipo_conta": row[8],  # CREDIT_CARD, CHECKING, SAVINGS
                "fonte": "open_finance",  # 🏦 Identificador de origem
                "banco": _mapear_banco_por_connector(row[9])  # Nome do banco
            }
            transacoes.append(transacao)
        
        logger.info(f"✅ {len(transacoes)} transações bancárias encontradas para user {user_id}")
        return transacoes
        
    except Exception as e:
        logger.warning(f"⚠️ Erro ao buscar transações Open Finance: {e}")
        return []  # Retorna lista vazia se Open Finance não estiver configurado

def _mapear_banco_por_connector(connector_id: int) -> str:
    """
    Mapeia connector_id para nome do banco.
    
    IDs comuns (Pluggy):
    - 201: Nubank
    - 205: Inter
    - 208: C6 Bank
    - 207: Banco do Brasil
    """
    mapeamento = {
        201: "Nubank",
        205: "Banco Inter",
        208: "C6 Bank",
        207: "Banco do Brasil",
        209: "Itaú",
        210: "Bradesco",
        211: "Santander",
        212: "Caixa"
    }
    return mapeamento.get(connector_id, f"Banco {connector_id}")