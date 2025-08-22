from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..models import models
from .auth import get_current_user
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
import os

router = APIRouter(prefix="/relatorios", tags=["Relatórios"])

@router.get("/pdf", response_class=Response)
def gerar_relatorio_pdf(
    mes: int,
    ano: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    """
    Gera um relatório financeiro em PDF para o usuário autenticado.
    """
    # Exemplo: buscar lançamentos do usuário no mês/ano
    lancamentos = db.query(models.Lancamento).filter(
        models.Lancamento.id_usuario == current_user.id,
        models.Lancamento.data_transacao.month == mes,
        models.Lancamento.data_transacao.year == ano
    ).all()
    # Carregar template Jinja2
    templates_path = os.path.join(os.path.dirname(__file__), '..', 'templates')
    env = Environment(loader=FileSystemLoader(templates_path), autoescape=True)
    template = env.get_template('relatorio.html')
    html_content = template.render(lancamentos=lancamentos, usuario=current_user, mes=mes, ano=ano)
    # Gerar PDF
    pdf_bytes = HTML(string=html_content).write_pdf()
    return Response(content=pdf_bytes, media_type="application/pdf")
