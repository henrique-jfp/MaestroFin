#!/usr/bin/env python3
"""
Demonstração das Funcionalidades de Machine Learning do MaestroFin
================================================================

Este script demonstra todas as funcionalidades avançadas de ML implementadas na Fase 3.
"""

import sys
import os
sys.path.append('.')

from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from gerente_financeiro.ml_engine import maestro_ml

def criar_dados_exemplo():
    """
    Cria dados financeiros de exemplo para demonstração
    """
    print("🔧 Criando dados de exemplo...")
    
    # Simular 6 meses de transações
    dados = []
    base_date = datetime.now() - timedelta(days=180)
    
    # Categorias e padrões típicos
    categorias_gastos = {
        'Alimentação': {'min': 15, 'max': 80, 'freq': 0.3},
        'Transporte': {'min': 10, 'max': 50, 'freq': 0.2},
        'Moradia': {'min': 800, 'max': 1200, 'freq': 0.05},
        'Lazer': {'min': 20, 'max': 150, 'freq': 0.15},
        'Saúde': {'min': 30, 'max': 200, 'freq': 0.1},
        'Educação': {'min': 100, 'max': 500, 'freq': 0.05},
        'Vestuário': {'min': 50, 'max': 300, 'freq': 0.08},
        'Diversos': {'min': 10, 'max': 100, 'freq': 0.07}
    }
    
    # Gerar transações realistas
    for i in range(500):  # 500 transações
        data = base_date + timedelta(days=np.random.randint(0, 180))
        
        # Escolher categoria baseada na frequência
        categoria = np.random.choice(
            list(categorias_gastos.keys()),
            p=[cat['freq'] for cat in categorias_gastos.values()]
        )
        
        # Valor baseado na categoria
        cat_info = categorias_gastos[categoria]
        valor = np.random.uniform(cat_info['min'], cat_info['max'])
        
        # Adicionar algumas receitas
        if np.random.random() < 0.1:  # 10% receitas
            categoria = 'Salário' if np.random.random() < 0.7 else 'Freelance'
            valor = np.random.uniform(2000, 5000)
            tipo = 'receita'
        else:
            tipo = 'despesa'
            valor = -valor
        
        # Descrições variadas
        descricoes = {
            'Alimentação': ['Supermercado', 'Restaurante', 'Lanchonete', 'Delivery', 'Padaria'],
            'Transporte': ['Uber', 'Combustível', 'Ônibus', 'Estacionamento', 'Taxi'],
            'Moradia': ['Aluguel', 'Condomínio', 'Energia', 'Água', 'Internet'],
            'Lazer': ['Cinema', 'Bar', 'Festa', 'Streaming', 'Show'],
            'Saúde': ['Farmácia', 'Médico', 'Exames', 'Plano de Saúde', 'Academia'],
            'Educação': ['Curso', 'Livros', 'Material', 'Mensalidade', 'Workshop'],
            'Vestuário': ['Roupa', 'Sapatos', 'Acessórios', 'Loja', 'Online'],
            'Diversos': ['Presente', 'Doação', 'Multa', 'Serviço', 'Reparo'],
            'Salário': ['Salário Empresa', 'Pagamento CLT', 'Folha Salarial'],
            'Freelance': ['Projeto', 'Consultoria', 'Trabalho Extra', 'Serviço']
        }
        
        descricao = np.random.choice(descricoes.get(categoria, ['Transação']))
        
        # Adicionar algumas anomalias intencionais
        if np.random.random() < 0.05:  # 5% anomalias
            valor *= np.random.uniform(3, 8)  # Gastos muito altos
        
        dados.append({
            'data': data,
            'valor': valor,
            'categoria': categoria,
            'descricao': descricao,
            'tipo': tipo,
            'dia_semana': data.weekday(),
            'dia_mes': data.day,
            'mes': data.month,
            'ano': data.year,
            'fim_semana': 1 if data.weekday() >= 5 else 0
        })
    
    return dados

def demonstrar_preparacao_dados():
    """
    Demonstra a preparação de dados para ML
    """
    print("\n🧠 === DEMONSTRAÇÃO: PREPARAÇÃO DE DADOS ===")
    
    # Simular objetos Lancamento
    class MockLancamento:
        def __init__(self, data_dict):
            for key, value in data_dict.items():
                setattr(self, key, value)
    
    dados_exemplo = criar_dados_exemplo()
    lancamentos_mock = [MockLancamento(d) for d in dados_exemplo]
    
    # Preparar dados para ML
    df = maestro_ml.preparar_dados_ml(lancamentos_mock)
    
    print(f"✅ Dataset preparado: {len(df)} transações")
    print(f"✅ Features criadas: {list(df.columns)}")
    print(f"✅ Período: {df['data'].min()} a {df['data'].max()}")
    print(f"✅ Categorias únicas: {df['categoria'].nunique()}")
    
    return df, lancamentos_mock

def demonstrar_classificacao():
    """
    Demonstra o treinamento e uso do classificador
    """
    print("\n🎯 === DEMONSTRAÇÃO: CLASSIFICAÇÃO AUTOMÁTICA ===")
    
    df, _ = demonstrar_preparacao_dados()
    
    # Treinar classificador
    resultado_treino = maestro_ml.treinar_classificador_categorias(df)
    
    if "erro" in resultado_treino:
        print(f"❌ Erro no treinamento: {resultado_treino['erro']}")
        return
    
    print(f"✅ Modelo treinado com {resultado_treino['accuracy']*100:.1f}% de precisão")
    print(f"✅ {resultado_treino['categorias_unicas']} categorias diferentes")
    print(f"✅ {resultado_treino['total_amostras']} amostras de treinamento")
    
    # Testar classificação
    test_cases = [
        (-50.0, "Supermercado Extra", datetime.now()),
        (-25.0, "Uber para o trabalho", datetime.now()),
        (-800.0, "Aluguel apartamento", datetime.now()),
        (-35.0, "Cinema Cinemark", datetime.now()),
        (3000.0, "Salário mensal", datetime.now())
    ]
    
    print("\n🧪 Testando classificação automática:")
    for valor, descricao, data in test_cases:
        categoria = maestro_ml.classificar_transacao(valor, descricao, data)
        print(f"   💰 R$ {valor:.2f} - '{descricao}' → {categoria}")

def demonstrar_anomalias():
    """
    Demonstra detecção de anomalias
    """
    print("\n⚠️ === DEMONSTRAÇÃO: DETECÇÃO DE ANOMALIAS ===")
    
    df, _ = demonstrar_preparacao_dados()
    
    resultado = maestro_ml.detectar_anomalias_avancadas(df)
    
    if "anomalias" not in resultado:
        print("❌ Erro na detecção de anomalias")
        return
    
    print(f"✅ {resultado['total_anomalias']} anomalias detectadas")
    print(f"✅ {resultado['percentual_anomalias']:.1f}% do total de transações")
    
    # Mostrar algumas anomalias
    for i, anomalia in enumerate(resultado['anomalias'][:3]):
        print(f"\n🔍 Anomalia {i+1}:")
        print(f"   📅 Data: {anomalia['data']}")
        print(f"   💰 Valor: R$ {abs(anomalia['valor']):.2f}")
        print(f"   🏷️ Categoria: {anomalia['categoria']}")
        print(f"   📝 Descrição: {anomalia['descricao']}")
        print(f"   ❓ Motivo: {anomalia['motivo']}")

def demonstrar_previsoes():
    """
    Demonstra previsão de gastos
    """
    print("\n🔮 === DEMONSTRAÇÃO: PREVISÃO DE GASTOS ===")
    
    df, _ = demonstrar_preparacao_dados()
    
    resultado = maestro_ml.prever_gastos_proximos_meses(df, meses_previsao=3)
    
    if "erro" in resultado:
        print(f"❌ Erro na previsão: {resultado['erro']}")
        return
    
    print(f"✅ Tendência detectada: {resultado['tendencia']}")
    print(f"✅ Variação média mensal: R$ {resultado['variacao_media_mensal']:.2f}")
    print(f"✅ Precisão do modelo: {resultado['r2_score']*100:.1f}%")
    
    print("\n📊 Previsões:")
    for previsao in resultado['previsoes']:
        print(f"   📅 {previsao['mes']}: R$ {previsao['previsao_gasto']:.2f} (Confiança: {previsao['confianca']})")

def demonstrar_clustering():
    """
    Demonstra análise de clusters
    """
    print("\n🎯 === DEMONSTRAÇÃO: ANÁLISE DE CLUSTERS ===")
    
    df, _ = demonstrar_preparacao_dados()
    
    resultado = maestro_ml.clustering_comportamento_financeiro(df)
    
    if "erro" in resultado:
        print(f"❌ Erro no clustering: {resultado['erro']}")
        return
    
    print(f"✅ {resultado['numero_clusters']} padrões comportamentais identificados")
    
    for i, cluster in enumerate(resultado['clusters']):
        print(f"\n🔸 Padrão {i+1}:")
        print(f"   👥 Tamanho: {cluster['tamanho']} transações")
        print(f"   💰 Valor médio: R$ {cluster['valor_medio']:.2f}")
        print(f"   📝 Comportamento: {cluster['descricao_comportamento']}")
        
        # Principais categorias
        categorias = cluster['categorias_principais']
        if categorias:
            principais = list(categorias.items())[:2]
            print(f"   🏷️ Principais: {', '.join([f'{cat} ({qtd})' for cat, qtd in principais])}")

def demonstrar_score_saude():
    """
    Demonstra cálculo do score de saúde financeira
    """
    print("\n📊 === DEMONSTRAÇÃO: SCORE DE SAÚDE FINANCEIRA ===")
    
    df, _ = demonstrar_preparacao_dados()
    
    resultado = maestro_ml.gerar_score_saude_financeira(df)
    
    print(f"✅ Score: {resultado['score']}/100")
    print(f"✅ Nível: {resultado['emoji']} {resultado['nivel']}")
    
    print("\n📈 Componentes do Score:")
    detalhes = resultado['detalhes']
    print(f"   💰 Taxa de Poupança: {detalhes['taxa_poupanca']:.1f}%")
    print(f"   📊 Consistência: {detalhes['consistencia']:.1f}%")
    print(f"   🎯 Diversificação: {detalhes['diversificacao']:.1f}%")
    print(f"   🔍 Controle de Gastos: {detalhes['controle_gastos']:.1f}%")
    
    print("\n💡 Recomendações:")
    for rec in resultado['recomendacoes']:
        print(f"   • {rec}")

def main():
    """
    Executa todas as demonstrações
    """
    print("🎉 DEMONSTRAÇÃO COMPLETA - MAESTROFIN MACHINE LEARNING")
    print("=" * 60)
    
    try:
        demonstrar_preparacao_dados()
        demonstrar_classificacao()
        demonstrar_anomalias()
        demonstrar_previsoes()
        demonstrar_clustering()
        demonstrar_score_saude()
        
        print("\n" + "=" * 60)
        print("🎉 DEMONSTRAÇÃO CONCLUÍDA COM SUCESSO!")
        print("✅ Todas as funcionalidades de ML estão operacionais")
        print("🚀 O MaestroFin está pronto para análises inteligentes!")
        
    except Exception as e:
        print(f"\n❌ Erro durante a demonstração: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
