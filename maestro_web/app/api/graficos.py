from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..models import models
from .auth import get_current_user
from typing import List
import pandas as pd

router = APIRouter(prefix="/graficos", tags=["Gráficos"])

@router.get("/gastos-por-categoria")
def grafico_gastos_por_categoria(
    mes: int,
    ano: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    """
    Retorna dados agregados de gastos por categoria para o usuário autenticado.
    """
    lancamentos = db.query(models.Lancamento).filter(
        models.Lancamento.id_usuario == current_user.id,
        models.Lancamento.data_transacao.month == mes,
        models.Lancamento.data_transacao.year == ano,
        models.Lancamento.tipo == "Saída"
    ).all()
    # Agregação simples (pode ser expandida)
    dados = {}
    for l in lancamentos:
        categoria = l.categoria.nome if l.categoria else "Sem Categoria"
        dados[categoria] = dados.get(categoria, 0) + float(l.valor)
    return dados

@router.get("/evolucao-saldo")
def grafico_evolucao_saldo(
    ano: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    """
    Retorna a evolução do saldo mês a mês para o usuário autenticado.
    """
    lancamentos = db.query(models.Lancamento).filter(
        models.Lancamento.id_usuario == current_user.id,
        models.Lancamento.data_transacao.year == ano
    ).all()
    # Agregação por mês
    saldo_mensal = {}
    for l in lancamentos:
        mes = l.data_transacao.month
        saldo_mensal.setdefault(mes, 0)
        if l.tipo == "Entrada":
            saldo_mensal[mes] += float(l.valor)
        else:
            saldo_mensal[mes] -= float(l.valor)
    return saldo_mensal
