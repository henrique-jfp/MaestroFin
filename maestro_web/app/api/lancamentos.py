# app/api/lancamentos.py
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..models import schemas, models
from .auth import get_current_user

router = APIRouter(prefix="/lancamentos", tags=["Lançamentos"])

@router.post("/", response_model=schemas.Lancamento, status_code=status.HTTP_201_CREATED)
def create_lancamento(
    lancamento: schemas.LancamentoCreate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    """
    Cria um novo lançamento para o usuário logado.
    Substitui o fluxo de 'lancamento manual'.
    """
    # Cria o objeto do banco de dados a partir dos dados recebidos
    db_lancamento = models.Lancamento(
        **lancamento.model_dump(),
        id_usuario=current_user.id
    )
    db.add(db_lancamento)
    db.commit()
    db.refresh(db_lancamento)
    return db_lancamento

@router.get("/", response_model=List[schemas.Lancamento])
def read_lancamentos(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    """
    Lista os lançamentos do usuário logado.
    """
    lancamentos = db.query(models.Lancamento).filter(
        models.Lancamento.id_usuario == current_user.id
    ).order_by(models.Lancamento.data_transacao.desc()).offset(skip).limit(limit).all()
    return lancamentos

@router.put("/{lancamento_id}", response_model=schemas.Lancamento)
def update_lancamento(
    lancamento_id: int,
    lancamento_update: schemas.LancamentoUpdate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    """
    Atualiza um lançamento existente.
    Substitui a lógica de 'editar'.
    """
    db_lancamento = db.query(models.Lancamento).filter(
        models.Lancamento.id == lancamento_id,
        models.Lancamento.id_usuario == current_user.id
    ).first()

    if db_lancamento is None:
        raise HTTPException(status_code=404, detail="Lançamento não encontrado")

    # Atualiza os campos fornecidos
    update_data = lancamento_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_lancamento, key, value)

    db.add(db_lancamento)
    db.commit()
    db.refresh(db_lancamento)
    return db_lancamento

@router.delete("/{lancamento_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lancamento(
    lancamento_id: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    """
    Deleta um lançamento.
    Substitui a lógica de 'apagar' do handler de edição.
    """
    db_lancamento = db.query(models.Lancamento).filter(
        models.Lancamento.id == lancamento_id,
        models.Lancamento.id_usuario == current_user.id
    ).first()

    if db_lancamento is None:
        raise HTTPException(status_code=404, detail="Lançamento não encontrado")

    db.delete(db_lancamento)
    db.commit()
    return None # Retorna uma resposta vazia com status 204

# Endpoints temporários sem autenticação para teste
@router.get("/test", response_model=List[schemas.Lancamento])
def test_read_lancamentos(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Lista os lançamentos (sem autenticação - apenas para teste).
    """
    lancamentos = db.query(models.Lancamento).order_by(models.Lancamento.data_transacao.desc()).offset(skip).limit(limit).all()
    return lancamentos

@router.post("/test", response_model=schemas.Lancamento, status_code=status.HTTP_201_CREATED)
def test_create_lancamento(
    lancamento: schemas.LancamentoCreateFrontend,
    db: Session = Depends(get_db)
):
    """
    Cria um novo lançamento (sem autenticação - apenas para teste).
    """
    # Converte o tipo para o formato esperado pelo banco
    tipo_db = "Entrada" if lancamento.tipo == "receita" else "Saída"
    
    # Cria o objeto do banco de dados a partir dos dados recebidos
    db_lancamento = models.Lancamento(
        descricao=lancamento.descricao,
        valor=lancamento.valor,
        tipo=tipo_db,
        data_transacao=lancamento.data_transacao,
        forma_pagamento=lancamento.forma_pagamento,
        id_conta=lancamento.id_conta,
        id_usuario=1  # Hardcoded para teste
    )
    db.add(db_lancamento)
    db.commit()
    db.refresh(db_lancamento)
    return db_lancamento

@router.delete("/test/{lancamento_id}", status_code=status.HTTP_204_NO_CONTENT)
def test_delete_lancamento(
    lancamento_id: int,
    db: Session = Depends(get_db)
):
    """
    Deleta um lançamento (sem autenticação - apenas para teste).
    """
    db_lancamento = db.query(models.Lancamento).filter(
        models.Lancamento.id == lancamento_id
    ).first()

    if db_lancamento is None:
        raise HTTPException(status_code=404, detail="Lançamento não encontrado")

    db.delete(db_lancamento)
    db.commit()
    return None # Retorna uma resposta vazia com status 204