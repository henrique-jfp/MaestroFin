#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🌐 MaestroFin Dashboard Web
Dashboard interativo para visualização de dados financeiros
"""

from flask import Flask, render_template, jsonify, request, redirect, url_for
from flask_cors import CORS
import plotly.graph_objects as go
import plotly.express as px
from plotly.utils import PlotlyJSONEncoder
import json
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
import logging
import os
import uuid

# --- IMPORTAÇÕES CORRIGIDAS ---
# Reutilizando a lógica de banco de dados e modelos existentes
from database.database import get_db, buscar_lancamentos_usuario
from models import Categoria, Objetivo, Usuario

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inicializar Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'maestrofin-dashboard-2025')
CORS(app)

# Configuração JSON Encoder para Plotly
app.json_encoder = PlotlyJSONEncoder

# Tokens válidos (em produção, usar Redis ou banco)
tokens_validos = {}

class DashboardService:
    """Serviço para gerar dados do dashboard"""
    
    def get_user_data(self, user_id: int, mes: int = None, ano: int = None):
        """Busca dados reais do usuário no banco e monta KPIs."""
        if not mes:
            mes = datetime.now().month
        if not ano:
            ano = datetime.now().year

        db = next(get_db())
        try:
            usuario = db.query(Usuario).filter(Usuario.telegram_id == user_id).first()
            if not usuario:
                return self.get_demo_data() # Retorna demo se usuário não existir

            # Definir o período para a busca
            data_inicio = datetime(ano, mes, 1)
            data_fim = (data_inicio + timedelta(days=32)).replace(day=1) - timedelta(days=1)

            # Reutilizar a função de busca de lançamentos
            lancamentos = buscar_lancamentos_usuario(
                telegram_user_id=user_id,
                limit=1000, # Limite alto para pegar todos do mês
                data_inicio=data_inicio,
                data_fim=data_fim
            )

            # KPIs
            receita_total = sum(l.valor for l in lancamentos if l.tipo.lower() == 'entrada')
            despesa_total = sum(l.valor for l in lancamentos if l.tipo.lower() == 'saída')
            saldo_mes = receita_total - despesa_total
            taxa_poupanca = (saldo_mes / receita_total * 100) if receita_total > 0 else 0
            qtd_transacoes = len(lancamentos)
            dias_com_gastos = len(set(l.data_transacao.date() for l in lancamentos if l.tipo.lower() == 'saída'))
            gasto_medio_dia = despesa_total / max(1, dias_com_gastos)

            # Gastos por categoria
            gastos_categorias_dict = {}
            for l in lancamentos:
                if l.tipo.lower() == 'saída' and l.categoria:
                    cat_nome = l.categoria.nome
                    gastos_categorias_dict[cat_nome] = gastos_categorias_dict.get(cat_nome, 0) + float(l.valor)
            
            gastos_categorias = sorted(gastos_categorias_dict.items(), key=lambda item: item[1], reverse=True)


            # Metas do usuário
            metas = db.query(Objetivo).filter(Objetivo.id_usuario == usuario.id).all()
            metas_serializadas = [
                {
                    'nome': m.descricao,
                    # CORREÇÃO: Renomeado de 'valor_meta' para 'valor_limite' para corresponder ao template.
                    # O template (main.html) espera 'meta.valor_limite' para calcular o progresso.
                    'valor_limite': float(m.valor_meta),
                    'valor_atual': float(m.valor_atual),
                    'data_meta': m.data_meta.strftime('%d/%m/%Y') if m.data_meta else None,
                    'progresso': (float(m.valor_atual) / float(m.valor_meta) * 100) if m.valor_meta > 0 else 0
                }
                for m in metas
            ]

            # Lançamentos serializados
            lancamentos_serializados = sorted([
                {
                    'data_transacao': l.data_transacao,
                    'descricao': l.descricao,
                    'categoria_nome': l.categoria.nome if l.categoria else 'N/A',
                    'tipo': l.tipo,
                    'valor': float(l.valor)
                }
                for l in lancamentos
            ], key=lambda x: x['data_transacao'], reverse=True)

            return {
                'kpis': {
                    'receita_total': float(receita_total),
                    'despesa_total': float(despesa_total),
                    'saldo_mes': float(saldo_mes),
                    'taxa_poupanca': float(taxa_poupanca),
                    'qtd_transacoes': qtd_transacoes,
                    'gasto_medio_dia': float(gasto_medio_dia)
                },
                'lancamentos': lancamentos_serializados,
                'metas': metas_serializadas,
                'gastos_categorias': gastos_categorias
            }
        except Exception as e:
            logger.error(f"Erro ao buscar dados reais do usuário: {e}", exc_info=True)
            return self.get_demo_data()
        finally:
            db.close()

    def get_demo_data(self):
        """Retorna dados de demonstração (sem alterações)"""
        return {
            'kpis': {
                'receita_total': 5500.00,
                'despesa_total': 4200.00,
                'saldo_mes': 1300.00,
                'taxa_poupanca': 23.6,
                'qtd_transacoes': 45,
                'gasto_medio_dia': 140.00
            },
            'lancamentos': [
                {
                    'data_transacao': datetime.now() - timedelta(days=i),
                    'descricao': f'Transação {i+1}',
                    'categoria_nome': ['Alimentação', 'Transporte', 'Lazer'][i % 3],
                    'tipo': 'Entrada' if i % 4 == 0 else 'Saída',
                    'valor': 100.00 + (i * 10)
                }
                for i in range(20)
            ],
            'metas': [],
            'gastos_categorias': [
                ['Alimentação', 1200.00],
                ['Transporte', 800.00],
                ['Moradia', 1500.00],
                ['Lazer', 450.00],
                ['Saúde', 250.00]
            ]
        }

dashboard_service = DashboardService()

@app.route('/')
def index():
    """Página inicial do dashboard"""
    return render_template('dashboard/index.html')

@app.route('/dashboard/<token>')
def dashboard_usuario(token):
    """Dashboard do usuário com token válido"""
    if token not in tokens_validos or tokens_validos[token]['expires'] < datetime.now():
        if token in tokens_validos:
            del tokens_validos[token]
        return redirect(url_for('token_invalido'))
    
    user_telegram_id = tokens_validos[token]['user_telegram_id']
    mes = request.args.get('mes', type=int, default=datetime.now().month)
    ano = request.args.get('ano', type=int, default=datetime.now().year)
    
    dados = dashboard_service.get_user_data(user_telegram_id, mes, ano)
    
    db = next(get_db())
    try:
        usuario = db.query(Usuario).filter(Usuario.telegram_id == user_telegram_id).first()
        nome_usuario = usuario.nome_completo if usuario else f'Usuário {user_telegram_id}'
    finally:
        db.close()

    return render_template('dashboard/main.html',
                         dados=dados,
                         kpis=dados['kpis'],
                         user_id=user_telegram_id,
                         mes=mes,
                         ano=ano,
                         usuario={'nome': nome_usuario},
                         now=datetime)

@app.route('/dashboard/demo')
def dashboard_demo():
    """Dashboard com dados de demonstração"""
    dados = dashboard_service.get_demo_data()
    return render_template('dashboard/main.html',
                         dados=dados,
                         kpis=dados['kpis'],
                         user_id=0, # ID 0 para demo
                         mes=datetime.now().month,
                         ano=datetime.now().year,
                         usuario={'nome': 'Usuário Demo'})

@app.route('/api/graficos/<int:user_id>')
def api_graficos(user_id):
    """API para gráficos do usuário"""
    mes = request.args.get('mes', type=int, default=datetime.now().month)
    ano = request.args.get('ano', type=int, default=datetime.now().year)
    
    dados = dashboard_service.get_user_data(user_id, mes, ano) if user_id != 0 else dashboard_service.get_demo_data()
    
    # Gráfico de pizza
    fig_pizza = px.pie(
        values=[gasto[1] for gasto in dados['gastos_categorias']],
        names=[gasto[0] for gasto in dados['gastos_categorias']],
        title="Gastos por Categoria"
    )
    
    return jsonify({
        'pizza': json.loads(json.dumps(fig_pizza, cls=PlotlyJSONEncoder))
    })

@app.route('/api/kpis/<int:user_id>')
def api_kpis(user_id):
    """API para KPIs do usuário"""
    mes = request.args.get('mes', type=int, default=datetime.now().month)
    ano = request.args.get('ano', type=int, default=datetime.now().year)
    
    dados = dashboard_service.get_user_data(user_id, mes, ano) if user_id != 0 else dashboard_service.get_demo_data()
    return jsonify(dados['kpis'])

@app.route('/api/gerar-token/<int:user_telegram_id>')
def gerar_token(user_telegram_id):
    """Gera token temporário para acesso ao dashboard"""
    token = str(uuid.uuid4())
    tokens_validos[token] = {
        'user_telegram_id': user_telegram_id,
        'criado': datetime.now(),
        'expires': datetime.now() + timedelta(minutes=10) # Duração curta por segurança
    }
    
    # Limpar tokens expirados
    agora = datetime.now()
    tokens_expirados = [t for t, data in list(tokens_validos.items()) if data['expires'] < agora]
    for t in tokens_expirados:
        del tokens_validos[t]
    
    return jsonify({
        'token': token,
        'url': url_for('dashboard_usuario', token=token, _external=False), # Retorna URL relativa
        'expires_in_minutes': 10
    })

@app.route('/api/status')
def api_status():
    """API para verificar status do dashboard"""
    return jsonify({
        'status': 'online',
        'timestamp': datetime.now().isoformat(),
        'version': '1.1.0',
        'tokens_ativos': len(tokens_validos)
    })

@app.route('/token-invalido')
def token_invalido():
    """Página de token inválido"""
    return render_template('dashboard/404.html', message="O link de acesso expirou ou é inválido. Por favor, gere um novo link no bot do Telegram com o comando /dashboard."), 401

@app.errorhandler(404)
def not_found(error):
    return render_template('dashboard/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Erro interno 500: {error}", exc_info=True)
    return render_template('dashboard/500.html'), 500

if __name__ == '__main__':
    print("🚀 Iniciando MaestroFin Dashboard...")
    print("📊 Dashboard disponível em: http://localhost:5000")
    print("🔗 Demo disponível em: http://localhost:5000/dashboard/demo")
    print("🔑 API para gerar token: /api/gerar-token/<user_telegram_id>")
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )