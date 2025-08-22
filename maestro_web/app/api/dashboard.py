# app/api/dashboard.py
from typing import Dict, List, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, and_
from datetime import datetime, timedelta

from ..core.database import get_db
from ..models import schemas, models
from .auth import get_current_user

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/overview", response_model=schemas.DashboardOverview)
def get_dashboard_overview(
    db: Session = Depends(get_db)
    # current_user: models.Usuario = Depends(get_current_user)
):
    """
    Retorna dados resumidos para o dashboard principal.
    """
    current_month = datetime.now().month
    current_year = datetime.now().year
    
    # Saldo total das contas (sem filtro de usuário por enquanto)
    total_balance = db.query(
        func.sum(models.Conta.saldo)
    ).scalar() or 0
    
    # Gastos do mês atual
    monthly_expenses = db.query(
        func.sum(models.Lancamento.valor)
    ).filter(
        models.Lancamento.id_usuario == current_user.id,
        models.Lancamento.tipo == "Saída",
        extract('month', models.Lancamento.data_transacao) == current_month,
        extract('year', models.Lancamento.data_transacao) == current_year
    ).scalar() or 0
    
    # Receitas do mês atual
    monthly_income = db.query(
        func.sum(models.Lancamento.valor)
    ).filter(
        models.Lancamento.id_usuario == current_user.id,
        models.Lancamento.tipo == "Entrada",
        extract('month', models.Lancamento.data_transacao) == current_month,
        extract('year', models.Lancamento.data_transacao) == current_year
    ).scalar() or 0
    
    # Metas ativas
    active_goals = db.query(func.count(models.Objetivo.id)).filter(
        models.Objetivo.id_usuario == current_user.id
    ).scalar() or 0
    
    # Progresso médio das metas
    avg_goal_progress = db.query(
        func.avg(models.Objetivo.valor_atual * 100.0 / models.Objetivo.valor_meta)
    ).filter(
        models.Objetivo.id_usuario == current_user.id,
        models.Objetivo.valor_meta > 0
    ).scalar() or 0
    
    # Transações recentes
    recent_transactions = db.query(models.Lancamento).filter(
        models.Lancamento.id_usuario == current_user.id
    ).order_by(models.Lancamento.data_transacao.desc()).limit(5).all()
    
    return schemas.DashboardOverview(
        total_balance=float(total_balance),
        monthly_expenses=float(monthly_expenses),
        monthly_income=float(monthly_income),
        monthly_balance=float(monthly_income - monthly_expenses),
        active_goals=active_goals,
        avg_goal_progress=float(avg_goal_progress),
        recent_transactions=[
            schemas.TransactionSummary(
                id=t.id,
                description=t.descricao,
                amount=float(t.valor),
                type=t.tipo,
                date=t.data_transacao,
                category=t.categoria.nome if t.categoria else None
            )
            for t in recent_transactions
        ]
    )

@router.get("/cards-data")
def get_cards_data(
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    """
    Retorna dados para os cards do sidebar.
    """
    # Contas
    accounts = db.query(models.Conta).filter(
        models.Conta.id_usuario == current_user.id
    ).all()
    
    # Categorias mais usadas
    top_categories = db.query(
        models.Categoria.nome,
        func.count(models.Lancamento.id).label('count'),
        func.sum(models.Lancamento.valor).label('total')
    ).join(models.Lancamento).filter(
        models.Lancamento.id_usuario == current_user.id,
        models.Lancamento.tipo == "Saída"
    ).group_by(models.Categoria.nome).order_by(
        func.count(models.Lancamento.id).desc()
    ).limit(5).all()
    
    # Metas próximas do prazo
    upcoming_goals = db.query(models.Objetivo).filter(
        models.Objetivo.id_usuario == current_user.id,
        models.Objetivo.data_meta.isnot(None),
        models.Objetivo.data_meta >= datetime.now().date(),
        models.Objetivo.data_meta <= (datetime.now() + timedelta(days=30)).date()
    ).order_by(models.Objetivo.data_meta).limit(3).all()
    
    # Agendamentos próximos
    upcoming_schedules = db.query(models.Agendamento).filter(
        models.Agendamento.id_usuario == current_user.id,
        models.Agendamento.ativo == True,
        models.Agendamento.proxima_execucao >= datetime.now(),
        models.Agendamento.proxima_execucao <= datetime.now() + timedelta(days=7)
    ).order_by(models.Agendamento.proxima_execucao).limit(3).all()
    
    return {
        "accounts": [
            {
                "id": acc.id,
                "name": acc.nome,
                "balance": float(acc.saldo),
                "type": acc.tipo
            }
            for acc in accounts
        ],
        "top_categories": [
            {
                "name": cat.nome,
                "count": cat.count,
                "total": float(cat.total)
            }
            for cat in top_categories
        ],
        "upcoming_goals": [
            {
                "id": goal.id,
                "description": goal.descricao,
                "target_value": float(goal.valor_meta),
                "current_value": float(goal.valor_atual),
                "progress": (float(goal.valor_atual) / float(goal.valor_meta)) * 100,
                "target_date": goal.data_meta.isoformat() if goal.data_meta else None
            }
            for goal in upcoming_goals
        ],
        "upcoming_schedules": [
            {
                "id": sched.id,
                "description": sched.descricao,
                "amount": float(sched.valor),
                "type": sched.tipo,
                "next_execution": sched.proxima_execucao.isoformat()
            }
            for sched in upcoming_schedules
        ]
    }

@router.get("/financial-health")
def get_financial_health(
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    """
    Calcula e retorna indicadores de saúde financeira.
    """
    current_month = datetime.now().month
    current_year = datetime.now().year
    
    # Receitas e gastos dos últimos 3 meses
    last_3_months = []
    for i in range(3):
        month = (current_month - i - 1) % 12 + 1
        year = current_year if current_month - i > 0 else current_year - 1
        
        income = db.query(
            func.sum(models.Lancamento.valor)
        ).filter(
            models.Lancamento.id_usuario == current_user.id,
            models.Lancamento.tipo == "Entrada",
            extract('month', models.Lancamento.data_transacao) == month,
            extract('year', models.Lancamento.data_transacao) == year
        ).scalar() or 0
        
        expenses = db.query(
            func.sum(models.Lancamento.valor)
        ).filter(
            models.Lancamento.id_usuario == current_user.id,
            models.Lancamento.tipo == "Saída",
            extract('month', models.Lancamento.data_transacao) == month,
            extract('year', models.Lancamento.data_transacao) == year
        ).scalar() or 0
        
        last_3_months.append({
            'month': month,
            'year': year,
            'income': float(income),
            'expenses': float(expenses),
            'balance': float(income - expenses)
        })
    
    # Cálculo dos indicadores
    avg_income = sum(m['income'] for m in last_3_months) / 3
    avg_expenses = sum(m['expenses'] for m in last_3_months) / 3
    avg_balance = sum(m['balance'] for m in last_3_months) / 3
    
    # Taxa de poupança
    savings_rate = (avg_balance / avg_income * 100) if avg_income > 0 else 0
    
    # Estabilidade (variação nos gastos)
    expense_variation = 0
    if len(last_3_months) >= 2:
        expenses_list = [m['expenses'] for m in last_3_months]
        avg_exp = sum(expenses_list) / len(expenses_list)
        expense_variation = sum(abs(exp - avg_exp) for exp in expenses_list) / len(expenses_list)
    
    stability_score = max(0, 100 - (expense_variation / avg_expenses * 100)) if avg_expenses > 0 else 100
    
    # Score geral de saúde financeira
    health_score = (
        min(savings_rate * 2, 40) +  # Máximo 40 pontos para poupança
        min(stability_score * 0.3, 30) +  # Máximo 30 pontos para estabilidade
        (30 if avg_balance > 0 else 0)  # 30 pontos se há superávit
    )
    
    return {
        "health_score": round(health_score, 1),
        "savings_rate": round(savings_rate, 1),
        "stability_score": round(stability_score, 1),
        "avg_monthly_income": round(avg_income, 2),
        "avg_monthly_expenses": round(avg_expenses, 2),
        "avg_monthly_balance": round(avg_balance, 2),
        "trend": "positive" if avg_balance > 0 else "negative",
        "last_3_months": last_3_months,
        "recommendations": _get_health_recommendations(health_score, savings_rate, stability_score)
    }

def _get_health_recommendations(health_score: float, savings_rate: float, stability_score: float) -> List[str]:
    """
    Gera recomendações baseadas na saúde financeira.
    """
    recommendations = []
    
    if health_score < 50:
        recommendations.append("🚨 Sua saúde financeira precisa de atenção urgente!")
    elif health_score < 70:
        recommendations.append("⚠️ Há espaço para melhorias na sua saúde financeira.")
    else:
        recommendations.append("✅ Sua saúde financeira está em bom estado!")
    
    if savings_rate < 10:
        recommendations.append("💰 Tente poupar pelo menos 10% da sua renda mensal.")
    elif savings_rate < 20:
        recommendations.append("💡 Considere aumentar sua taxa de poupança para 20%.")
    
    if stability_score < 60:
        recommendations.append("📊 Seus gastos estão variando muito. Tente criar um orçamento fixo.")
    
    return recommendations

@router.get("/simple", response_model=Dict[str, Any])
def get_dashboard_simple(db: Session = Depends(get_db)):
    """
    Retorna dados simples para o dashboard sem autenticação.
    """
    return {
        "saldo_total": 1000.0,
        "receitas_mes": 5000.0,
        "despesas_mes": 3500.0,
        "objetivos_atingidos": 2,
        "objetivos_total": 5,
        "lancamentos_recentes": [
            {
                "id": 1,
                "tipo": "receita",
                "valor": 500.0,
                "descricao": "Salário",
                "categoria": "Trabalho",
                "data": "2024-01-15",
                "conta": "Conta Corrente"
            },
            {
                "id": 2,
                "tipo": "despesa",
                "valor": 200.0,
                "descricao": "Supermercado",
                "categoria": "Alimentação",
                "data": "2024-01-14",
                "conta": "Conta Corrente"
            }
        ]
    }
