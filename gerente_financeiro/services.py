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
from sqlalchemy import func, and_, extract
import asyncio
import hashlib  # <-- Para gerar chaves de cache
import json  # <-- Para serialização de dados
from functools import lru_cache  # <-- Cache em memória
import google.generativeai as genai
from .prompts import PROMPT_ANALISE_RELATORIO
from database.database import listar_objetivos_usuario
from models import Categoria, Lancamento, Usuario, Subcategoria
import config
from . import external_data
from dateutil.relativedelta import relativedelta
import numpy as np 
from scipy.interpolate import make_interp_spline

# --- SISTEMA DE CACHE INTELIGENTE ---
_cache_financeiro = {}
_cache_tempo = {}
CACHE_TTL = 300  # 5 minutos em segundos

def _gerar_chave_cache(user_id: int, tipo: str, **parametros) -> str:
    """Gera uma chave única para cache baseada nos parâmetros"""
    dados_chave = {
        'user_id': user_id,
        'tipo': tipo,
        **parametros
    }
    texto_chave = json.dumps(dados_chave, sort_keys=True)
    return hashlib.md5(texto_chave.encode()).hexdigest()

def _cache_valido(chave: str) -> bool:
    """Verifica se o cache ainda é válido"""
    if chave not in _cache_tempo:
        return False
    tempo_cache = _cache_tempo[chave]
    tempo_atual = datetime.now().timestamp()
    return (tempo_atual - tempo_cache) < CACHE_TTL

def _obter_do_cache(chave: str) -> Any:
    """Obtém dados do cache se válido"""
    if _cache_valido(chave):
        return _cache_financeiro.get(chave)
    return None

def _salvar_no_cache(chave: str, dados: Any) -> None:
    """Salva dados no cache com timestamp"""
    _cache_financeiro[chave] = dados
    _cache_tempo[chave] = datetime.now().timestamp()
    
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
    data_inicio_historico = data_alvo - relativedelta(months=5)

    def buscar_dados_periodo(data_inicio, data_fim):
        # A busca já otimiza carregando a categoria junto
        return db.query(Lancamento).filter(
            and_(
                Lancamento.id_usuario == usuario_q.id,
                Lancamento.data_transacao >= data_inicio,
                Lancamento.data_transacao < data_fim
            )
        ).options(joinedload(Lancamento.categoria)).all()

    # Busca todos os lançamentos do período, incluindo transferências
    lancamentos_mes_atual = buscar_dados_periodo(data_alvo, data_alvo + relativedelta(months=1))
    lancamentos_historico_6m = buscar_dados_periodo(data_inicio_historico, data_alvo + relativedelta(months=1))

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
    receitas_atual = sum(float(l.valor) for l in lancamentos_financeiros if l.tipo == 'Entrada')
    despesas_atual = sum(float(l.valor) for l in lancamentos_financeiros if l.tipo == 'Saída')
    saldo_atual = receitas_atual - despesas_atual
    taxa_poupanca_atual = (saldo_atual / receitas_atual) * 100 if receitas_atual > 0 else 0

    # O agrupamento de gastos também usa a lista filtrada
    gastos_por_categoria_atual = {}
    for l in lancamentos_financeiros:
        if l.tipo == 'Saída' and l.valor > 0:
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
        
    if 'Entrada' not in dados_mensais.columns: dados_mensais['Entrada'] = 0
    if 'Saída' not in dados_mensais.columns: dados_mensais['Saída'] = 0

    periodo_3m = dados_mensais.index[dados_mensais.index < periodo_alvo][-3:]
    media_3m = dados_mensais.loc[periodo_3m].mean() if not periodo_3m.empty else pd.Series(dtype=float)
    media_receitas_3m = media_3m.get('Entrada', 0.0)
    media_despesas_3m = media_3m.get('Saída', 0.0)

    periodo_anterior = periodo_alvo - 1
    if periodo_anterior in dados_mensais.index:
        receitas_anterior = dados_mensais.loc[periodo_anterior, 'Entrada']
        despesas_anterior = dados_mensais.loc[periodo_anterior, 'Saída']
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
        
        if 'Entrada' not in df_agrupado.columns: df_agrupado['Entrada'] = 0
        if 'Saída' not in df_agrupado.columns: df_agrupado['Saída'] = 0
        
        df_agrupado = df_agrupado.sort_index()
        
        df_agrupado.index = df_agrupado.index.strftime('%b/%y')

        fig, ax = plt.subplots(figsize=(10, 5), dpi=100)
        
        ax.plot(df_agrupado.index, df_agrupado['Entrada'], marker='o', linestyle='-', color='#2ecc71', label='Receitas')
        ax.plot(df_agrupado.index, df_agrupado['Saída'], marker='o', linestyle='-', color='#e74c3c', label='Despesas')

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
        model = genai.GenerativeModel("gemini-1.5-flash")
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
    
    despesas_df = df[df['tipo'] == 'Saída'].copy()
    receitas_df = df[df['tipo'] == 'Entrada'].copy()
    
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

def definir_perfil_investidor(respostas: dict) -> str:
    pontos = 0
    risco = respostas.get('risco')
    if risco == 'baixo': pontos += 1
    elif risco == 'medio': pontos += 2
    elif risco == 'alto': pontos += 3
    prazo_texto = respostas.get('prazo', '').lower()
    numeros_encontrados = re.findall(r'\d+', prazo_texto)
    if numeros_encontrados:
        numero_prazo = int(numeros_encontrados[0])
        if "mes" in prazo_texto or "meses" in prazo_texto: pontos += 1
        elif numero_prazo <= 2: pontos += 1
        elif 2 < numero_prazo <= 5: pontos += 2
        else: pontos += 3
    else:
        if 'curto' in prazo_texto: pontos += 1
        elif 'médio' in prazo_texto: pontos += 2
        elif 'longo' in prazo_texto: pontos += 3
        else: pontos += 1
    if pontos <= 3: return 'Conservador'
    elif pontos <= 5: return 'Moderado'
    else: return 'Arrojado'

def preparar_dados_para_grafico(lancamentos: List[Lancamento], agrupar_por: str):
    if not lancamentos: return pd.DataFrame(), False
    dados_base = []
    if agrupar_por in ['categoria', 'forma_pagamento']:
        lista_base = [l for l in lancamentos if l.tipo == 'Saída']
        if not lista_base: return pd.DataFrame(), False
        for l in lista_base:
            grupo = ""
            if agrupar_por == 'categoria':
                grupo = l.categoria.nome if l.categoria else "Sem Categoria"
            elif agrupar_por == 'forma_pagamento':
                grupo = l.forma_pagamento or "Não Especificado"
            dados_base.append({'grupo': grupo, 'valor': float(l.valor)})
        if not dados_base: return pd.DataFrame(), False
        df = pd.DataFrame(dados_base)
        df_agrupado = df.groupby('grupo')['valor'].sum().reset_index().sort_values('valor', ascending=False)
        if len(df_agrupado) > 7:
            top_7 = df_agrupado.iloc[:6].copy()
            outros_valor = df_agrupado.iloc[6:]['valor'].sum()
            outros_df = pd.DataFrame([{'grupo': 'Outros', 'valor': outros_valor}])
            df_agrupado = pd.concat([top_7, outros_df], ignore_index=True)
        return df_agrupado, not df_agrupado.empty
    elif agrupar_por in ['data', 'fluxo_caixa', 'projecao']:
        for l in lancamentos:
            dados_base.append({'data': l.data_transacao.date(), 'valor': float(l.valor), 'tipo': l.tipo})
        if not dados_base: return pd.DataFrame(), False
        df = pd.DataFrame(dados_base)
        df_agrupado = df.groupby(['data', 'tipo'])['valor'].sum().unstack(fill_value=0)
        if 'Entrada' not in df_agrupado.columns: df_agrupado['Entrada'] = 0
        if 'Saída' not in df_agrupado.columns: df_agrupado['Saída'] = 0
        df_agrupado = df_agrupado.reset_index().sort_values('data')
        if agrupar_por == 'data':
            df_agrupado['Saldo'] = df_agrupado['Entrada'] - df_agrupado['Saída']
            df_agrupado['Saldo Acumulado'] = df_agrupado['Saldo'].cumsum()
        if agrupar_por == 'projecao' and df_agrupado['Saída'].sum() == 0:
            return pd.DataFrame(), False
        return df_agrupado, len(df_agrupado) >= 1
    return pd.DataFrame(), False

def categorizar_transacao(descricao: str):
    desc = descricao.lower()
    regras = [
    # ALIMENTAÇÃO
    (r'ifood|rappi|uber eats|james delivery', 'Alimentação', 'Delivery'),
    (r'mercado|supermercado|hortifruti|sams club|carrefour|pao de acucar|extra', 'Alimentação', 'Supermercado'),
    (r'restaurante|churrascaria|pizzaria|outback', 'Alimentação', 'Restaurante'),
    (r'lanche|cafe|padaria|starbucks|dunkin|burger king|mcdonald\'s|kfc|bk', 'Alimentação', 'Lanches e Cafés'),

    # MORADIA
    (r'aluguel|condominio', 'Moradia', 'Aluguel e Condomínio'),
    (r'light|enel|naturgy|aguas do rio|cedae|conta de luz|gas|agua', 'Moradia', 'Contas de Consumo'),
    (r'leroy merlin|telhanorte|manutencao|reparo', 'Moradia', 'Manutenção e Reparos'),
    (r'tok&stok|etna|madeira madeira|moveis|decoracao', 'Moradia', 'Móveis e Decoração'),

    # TRANSPORTE
    (r'uber|99pop|99|cabify', 'Transporte', 'App de Corrida'),
    (r'posto|shell|ipiranga|petrobras|br distribuidora|combustivel', 'Transporte', 'Combustível'),
    (r'metro rio|supervia|vlt|bilhete unico|riocard|onibus', 'Transporte', 'Transporte Público'),
    (r'estacionamento|parking', 'Transporte', 'Estacionamento'),
    (r'pedagio|sem parar|conectcar|taggy', 'Transporte', 'Pedágio'),
    (r'oficina|troca de oleo|pneu|mecanico|autopecas', 'Transporte', 'Manutenção Veicular'),

    # SAÚDE
    (r'farmacia|drogaria|drogasil|pacheco|droga raia', 'Saúde', 'Farmácia'),
    (r'consulta|exame|laboratorio|clinica|hospital', 'Saúde', 'Consultas e Exames'),
    (r'plano de saude|unimed|bradesco saude|amil|sulamerica', 'Saúde', 'Plano de Saúde'),

    # LAZER
    (r'cinema|ingresso|show|ticket|eventim|sympla', 'Lazer', 'Cinema e Shows'),
    (r'viagem|hotel|decolar|booking|latam|gol|azul|cvc|passagem aerea', 'Lazer', 'Viagens'),
    (r'bar|pub|balada|boate', 'Lazer', 'Bares e Baladas'),
    (r'esporte|academia|smart fit|bodytech|decathlon', 'Lazer', 'Hobbies e Esportes'),
    (r'livraria|papelaria|saraiva|cultura|kalunga', 'Lazer', 'Livros e Papelaria'),

    # COMPRAS
    (r'roupa|loja|renner|c&a|riachuelo|zara|marisa|vestuario', 'Compras', 'Roupas e Acessórios'),
    (r'ponto frio|casas bahia|magazine luiza|magalu|fast shop|polishop', 'Compras', 'Eletrônicos'),
    (r'presente', 'Compras', 'Presentes'),
    
    # CUIDADOS PESSOAIS
    (r'salao|barbearia|cabelo|manicure|pedicure', 'Cuidados Pessoais', 'Salão e Barbearia'),
    (r'cosmetico|o boticario|natura|sephora', 'Cuidados Pessoais', 'Cosméticos'),

    # EDUCAÇÃO
    (r'curso|faculdade|universidade|mensalidade|ead', 'Educação', 'Cursos e Faculdades'),
    (r'material escolar', 'Educação', 'Material Escolar'),

    # ASSINATURAS
    (r'netflix|spotify|prime video|amazon prime|hbo|disney|globoplay|deezer|youtube premium', 'Assinaturas', 'Streaming'),
    (r'net|claro|vivo|oi|tim|internet|tv por assinatura', 'Assinaturas', 'TV e Internet'),
    (r'adobe|microsoft|google|icloud|software', 'Assinaturas', 'Software e Apps'),

    # SERVIÇOS FINANCEIROS E IMPOSTOS
    (r'pag[- ]?amento.*boleto|pagto boleto', 'Pagamentos', 'Boleto'),
    (r'tarifa|juros|taxa|iof', 'Serviços', 'Serviços Financeiros'),
    (r'imposto|iptu|ipva|irpf|darf', 'Impostos', 'Impostos'),
    
    # TRANSFERÊNCIAS E SAQUES
    (r'pix', 'Transferências', 'Pix'),
    (r'ted|doc', 'Transferências', 'TED/DOC'),
    (r'transferencia', 'Transferências', 'Outras'), # Regra genérica para transferências
    (r'saque|retirada', 'Outros', 'Saques'),

    # INVESTIMENTOS
    (r'tesouro direto|cdb|lci|lca', 'Investimentos', 'Renda Fixa'),
    (r'b3|acoes|fundos imobiliarios|corretora', 'Investimentos', 'Renda Variável'),

    # OUTROS
    (r'doacao|doar', 'Doações', 'Doações'),
]
    
    for pattern, cat, sub in regras:
        if re.search(pattern, desc):
            return cat, sub
    return 'Outros', 'Geral'

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
                ax.set_title(f'Distribuição de Despesas por {agrupar_por.replace("_", " ").title()}', pad=20)
                
                # Paleta de cores mais bonita (Set2 é boa para categorias distintas)
                colors = plt.cm.Set2(np.linspace(0, 1, len(df['grupo'])))
                
                # Explode as fatias para melhor visualização
                explode = [0.05] * len(df['grupo'])
                
                wedges, texts, autotexts = ax.pie(
                    df['valor'], 
                    autopct='%1.1f%%', 
                    startangle=90, 
                    colors=colors, 
                    pctdistance=0.85,
                    explode=explode,
                    wedgeprops={'edgecolor': 'white', 'linewidth': 2}
                )
                plt.setp(autotexts, size=12, weight="bold", color="white")
                
                # Desenha o círculo no centro para criar o efeito DONUT
                centre_circle = plt.Circle((0,0), 0.70, fc='white')
                fig.gca().add_artist(centre_circle)
                
                # Legenda limpa e organizada
                legend_labels = [f"{label}: R$ {valor:.2f}" for label, valor in zip(df['grupo'], df['valor'])]
                ax.legend(wedges, legend_labels, title="Valores", loc="center left", bbox_to_anchor=(1, 0, 0.5, 1), fontsize=11)
                ax.axis('equal')

            # GRÁFICO DE BARRAS HORIZONTAIS
            elif tipo_grafico == 'barra_h':
                ax.set_title(f'Total de Despesas por {agrupar_por.replace("_", " ").title()}', pad=20)
                df = df.sort_values('valor', ascending=True) # Ordena do menor para o maior
                
                palette = sns.color_palette("viridis_r", len(df))
                bars = ax.barh(df['grupo'], df['valor'], color=palette, edgecolor='black', linewidth=0.7)
                
                ax.set_xlabel('Valor Gasto (R$)', fontsize=12)
                ax.set_ylabel('')
                ax.grid(axis='y', linestyle='', alpha=0) # Remove linhas de grade horizontais
                
                # Rótulos de valor inteligentes
                for bar in bars:
                    width = bar.get_width()
                    ax.text(width + 50, bar.get_y() + bar.get_height()/2, f'R$ {width:,.2f}'.replace(',', '.'),
                            va='center', ha='left', fontsize=11, weight='bold', color=bar.get_facecolor())

        # --- GRÁFICOS BASEADOS EM DATA ---
        elif agrupar_por in ['data', 'fluxo_caixa', 'projecao']:
            df['data'] = pd.to_datetime(df['data'])
            
            # GRÁFICO DE EVOLUÇÃO DO SALDO (LINHA)
            if agrupar_por == 'data':
                if len(df) < 3: return None # Precisa de pelo menos 3 pontos para suavizar
                ax.set_title('Evolução do Saldo Financeiro', pad=20)
                
                # Suavização da linha
                x_smooth = np.linspace(df['data'].astype(np.int64).min(), df['data'].astype(np.int64).max(), 300)
                x_smooth_dt = pd.to_datetime(x_smooth)
                spl = make_interp_spline(df['data'].astype(np.int64), df['Saldo Acumulado'], k=2)
                y_smooth = spl(x_smooth)
                
                ax.plot(x_smooth_dt, y_smooth, label='Saldo Acumulado (suave)', color='#3498db', linewidth=3)
                ax.fill_between(x_smooth_dt, y_smooth, alpha=0.15, color='#3498db')
                
                # Destaque do pico máximo e mínimo
                pico_max = df.loc[df['Saldo Acumulado'].idxmax()]
                pico_min = df.loc[df['Saldo Acumulado'].idxmin()]
                
                ax.scatter(pico_max['data'], pico_max['Saldo Acumulado'], color='#2ecc71', s=150, zorder=5, label='Pico Máximo', edgecolor='white')
                ax.scatter(pico_min['data'], pico_min['Saldo Acumulado'], color='#e74c3c', s=150, zorder=5, label='Pico Mínimo', edgecolor='white')
                
                # Anotações nos picos
                ax.text(pico_max['data'], pico_max['Saldo Acumulado'] + 500, f'{pico_max["Saldo Acumulado"]:.0f}', ha='center', fontsize=12, weight='bold', color='black', backgroundcolor=(1,1,1,0.6))
                ax.text(pico_min['data'], pico_min['Saldo Acumulado'] - 1000, f'{pico_min["Saldo Acumulado"]:.0f}', ha='center', fontsize=12, weight='bold', color='black', backgroundcolor=(1,1,1,0.6))

                ax.legend(fontsize=12)

            # GRÁFICO DE PROJEÇÃO (BARRAS HORIZONTAIS)
            elif agrupar_por == 'projecao':
                today = datetime.now()
                start_of_month = today.replace(day=1, hour=0, minute=0, second=0).date()
                df_mes_atual = df[(df['data'].dt.date >= start_of_month) & (df['data'].dt.date <= today.date())]
                if df_mes_atual.empty or df_mes_atual['Saída'].sum() == 0: return None
                
                gasto_acumulado = df_mes_atual['Saída'].sum()
                dias_no_mes = (today.replace(month=today.month % 12 + 1 if today.month != 12 else 1, day=1) - timedelta(days=1)).day
                dias_passados = today.day
                gasto_medio_diario = gasto_acumulado / dias_passados
                gasto_projetado = gasto_medio_diario * dias_no_mes
                
                ax.set_title(f'Projeção de Gastos para {today.strftime("%B")}', pad=20)
                
                data_proj = {'Label': ['Gasto Atual', 'Projeção para o Mês'], 'Valor': [gasto_acumulado, gasto_projetado]}
                df_proj = pd.DataFrame(data_proj)

                bars = ax.barh(df_proj['Label'], df_proj['Valor'], color=['#1f77b4', '#ff7f0e'], edgecolor='black', linewidth=0.8)
                ax.invert_yaxis() # Gasto atual em cima
                
                ax.set_xlabel('Valor (R$)', fontsize=12)
                ax.bar_label(bars, fmt='R$ %.2f', padding=5, fontsize=12, weight='bold')

                # Caixa de anotação para o gasto médio
                ax.text(gasto_projetado * 0.95, 1, f'Gasto médio diário: R$ {gasto_medio_diario:.2f}',
                        va='center', ha='right', fontsize=11, style='italic',
                        bbox=dict(boxstyle='round,pad=0.5', fc='khaki', alpha=0.7))

            # GRÁFICO DE FLUXO DE CAIXA (Ainda mantido, mas menos focado)
            elif agrupar_por == 'fluxo_caixa':
                # (Lógica original mantida, pois não havia referência de melhoria)
                if df['Entrada'].sum() == 0 and df['Saída'].sum() == 0: return None
                ax.bar(df['data'], df['Entrada'], color='#2ecc71', label='Receitas', width=timedelta(days=0.8))
                ax.bar(df['data'], -df['Saída'], color='#e74c3c', label='Despesas', width=timedelta(days=0.8))
                ax.axhline(0, color='black', linewidth=0.8)
                ax.set_title('Fluxo de Caixa (Receitas vs. Despesas)', pad=20)
                ax.legend()
            
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
            if l.tipo == 'Saída' and l.categoria:
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
        gastos_weekend = [l for l in ultimos_30_dias if l.data_transacao.weekday() >= 5 and l.tipo == 'Saída']
        total_weekend = sum(float(l.valor) for l in gastos_weekend)
        total_geral = sum(float(l.valor) for l in ultimos_30_dias if l.tipo == 'Saída')
        
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
        if l.tipo == 'Saída':
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

async def preparar_contexto_financeiro_completo(db: Session, usuario: Usuario) -> str:
    """
    Coleta e formata um resumo completo do ecossistema financeiro do usuário.
    VERSÃO 5.0 - Com cache inteligente, análise comportamental avançada e dados externos.
    """
    # Limpeza automática de cache
    _limpar_cache_expirado()
    
    # Verifica cache primeiro
    chave_cache = _gerar_chave_cache(
        usuario.id, 
        'contexto_completo',
        timestamp=datetime.now().replace(minute=0, second=0, microsecond=0).timestamp()  # Cache por hora
    )
    
    dados_cache = _obter_do_cache(chave_cache)
    if dados_cache:
        logger.info(f"Contexto financeiro obtido do cache para usuário {usuario.id}")
        return dados_cache
    
    lancamentos = db.query(Lancamento).filter(Lancamento.id_usuario == usuario.id).options(
        joinedload(Lancamento.categoria)
    ).order_by(Lancamento.data_transacao.asc()).all()
    
    if not lancamentos:
        return json.dumps({"resumo": "Nenhum dado financeiro encontrado."}, indent=2, ensure_ascii=False)

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
        if l.tipo == 'Entrada':
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
    
    # Contexto completo com todas as melhorias da Fase 2
    contexto_completo = {
        "informacoes_gerais": {
            "data_atual": datetime.now().strftime('%d/%m/%Y'),
            "periodo_disponivel": f"{data_minima} a {data_maxima}",
            "contas_cadastradas": [c.nome for c in contas_db],
            "metas_financeiras": metas_financeiras,
            "insights_automaticos": _gerar_insights_automaticos(lancamentos),
            "padroes_detectados": _detectar_padroes_comportamentais(lancamentos),
            "estatisticas_cache": _obter_estatisticas_cache()
        },
        "analise_comportamental_avancada": analise_comportamental,
        "contexto_economico": {
            "dados_mercado": dados_mercado,
            "indicadores_economicos": dados_economicos,
            "situacao_comparativa": situacao_comparativa
        },
        "resumo_por_mes": resumo_mensal,
        "todos_lancamentos": [
            {
                "data": l.data_transacao.strftime('%Y-%m-%d'),
                "descricao": l.descricao,
                "valor": float(l.valor),
                "tipo": l.tipo,
                "categoria": l.categoria.nome if l.categoria else "Sem Categoria",
                "conta": l.forma_pagamento,
                "dia_semana": l.data_transacao.weekday(),
                "hora": l.data_transacao.hour
            } for l in lancamentos
        ]
    }

    resultado = json.dumps(contexto_completo, indent=2, ensure_ascii=False)
    
    # Salva no cache
    _salvar_no_cache(chave_cache, resultado)
    logger.info(f"Contexto financeiro completo v5.0 calculado e salvo no cache para usuário {usuario.id}")
    
    return resultado

# === SISTEMA DE INTEGRAÇÃO DE DADOS EXTERNOS ===

async def _obter_dados_mercado_financeiro() -> Dict[str, Any]:
    """
    Obtém dados de mercado financeiro para contextualizar investimentos
    Retorna dados mock para demonstração
    """
    try:
        # Dados mockados para demonstração - em produção, conectar com APIs reais
        return {
            "selic": 11.75,
            "ipca_acumulado_12m": 4.62,
            "cdi": 11.65,
            "dollar_rate": 5.12,
            "bitcoin_brl": 180000,
            "recomendacoes": [
                "Com a Selic alta, renda fixa está atrativa",
                "Inflação controlada favorece investimentos de longo prazo",
                "Diversificação é essencial no cenário atual"
            ],
            "data_atualizacao": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    except Exception as e:
        logger.error(f"Erro ao obter dados de mercado: {e}")
        return {}

async def _obter_dados_economicos_contexto() -> Dict[str, Any]:
    """
    Obtém dados econômicos para contextualizar análises
    """
    try:
        # Dados econômicos mockados
        return {
            "pib_crescimento": 2.3,
            "desemprego": 8.7,
            "salario_minimo": 1412.00,
            "renda_media_nacional": 2850.00,
            "alertas_economicos": [
                "PIB em crescimento moderado",
                "Taxa de desemprego em queda gradual",
                "Poder de compra estável"
            ]
        }
    except Exception as e:
        logger.error(f"Erro ao obter dados econômicos: {e}")
        return {}

async def _classificar_situacao_comparativa(economia_mensal: float, gastos_mensais: float) -> Dict[str, Any]:
    """
    Classifica a situação financeira do usuário comparando com dados nacionais
    """
    try:
        dados_economicos = await _obter_dados_economicos_contexto()
        renda_media = dados_economicos.get('renda_media_nacional', 2850)
        salario_minimo = dados_economicos.get('salario_minimo', 1412)
        
        # Calculações comparativas
        renda_estimada = gastos_mensais + economia_mensal
        percentil_renda = (renda_estimada / renda_media) * 100
        multiplos_salario_minimo = renda_estimada / salario_minimo
        
        # Classificação da situação
        if percentil_renda >= 150:
            situacao = "Acima da média nacional"
        elif percentil_renda >= 80:
            situacao = "Próximo à média nacional"
        elif percentil_renda >= 50:
            situacao = "Abaixo da média nacional"
        else:
            situacao = "Bem abaixo da média nacional"
        
        return {
            "situacao_comparativa": situacao,
            "percentil_renda": min(200, percentil_renda),
            "multiplos_salario_minimo": round(multiplos_salario_minimo, 1),
            "renda_estimada": renda_estimada,
            "benchmarks": {
                "renda_media_nacional": renda_media,
                "salario_minimo": salario_minimo
            }
        }
    except Exception as e:
        logger.error(f"Erro na classificação comparativa: {e}")
        return {}

# === SISTEMA DE LIMPEZA DE CACHE ===

def _limpar_cache_expirado():
    """
    Remove entradas expiradas do cache para otimizar memória
    """
    try:
        chaves_para_remover = []
        agora = time.time()
        
        for chave, dados in _cache_memoria.items():
            if dados['timestamp'] + dados['ttl'] < agora:
                chaves_para_remover.append(chave)
        
        for chave in chaves_para_remover:
            del _cache_memoria[chave]
        
        if chaves_para_remover:
            logger.info(f"Cache limpo: {len(chaves_para_remover)} entradas removidas")
            
    except Exception as e:
        logger.error(f"Erro na limpeza de cache: {e}")

def _obter_estatisticas_cache() -> Dict[str, Any]:
    """
    Retorna estatísticas do sistema de cache para monitoramento
    """
    try:
        total_entradas = len(_cache_memoria)
        agora = time.time()
        entradas_validas = 0
        entradas_expiradas = 0
        
        for dados in _cache_memoria.values():
            if dados['timestamp'] + dados['ttl'] >= agora:
                entradas_validas += 1
            else:
                entradas_expiradas += 1
        
        return {
            "total_entradas": total_entradas,
            "entradas_validas": entradas_validas,
            "entradas_expiradas": entradas_expiradas,
            "eficiencia": (entradas_validas / total_entradas * 100) if total_entradas > 0 else 0
        }
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas de cache: {e}")
        return {"erro": str(e)}

# === MELHORIAS NO SISTEMA DE CONTEXTO FINANCEIRO ===