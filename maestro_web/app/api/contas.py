from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..models import models, schemas
from .auth import get_current_user

router = APIRouter(prefix="/contas", tags=["Contas"])

@router.get("/", response_model=List[schemas.Conta])
def read_contas(
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    """
    Lista todas as contas do usuário logado.
    """
    contas = db.query(models.Conta).filter(models.Conta.id_usuario == current_user.id).all()
    return contas

@router.post("/", response_model=schemas.Conta, status_code=201)
def create_conta(
    conta: schemas.ContaCreate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    """
    Cria uma nova conta para o usuário autenticado.
    """
    nova_conta = models.Conta(
        nome=conta.nome,
        tipo=conta.tipo,
        dia_fechamento=conta.dia_fechamento,
        dia_vencimento=conta.dia_vencimento,
        id_usuario=current_user.id
    )
    db.add(nova_conta)
    db.commit()
    db.refresh(nova_conta)
    return nova_conta

@router.put("/{conta_id}", response_model=schemas.Conta)
def update_conta(
    conta_id: int,
    conta_update: schemas.ContaCreate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    """
    Atualiza uma conta existente do usuário autenticado.
    """
    db_conta = db.query(models.Conta).filter(
        models.Conta.id == conta_id,
        models.Conta.id_usuario == current_user.id
    ).first()
    if db_conta is None:
        raise HTTPException(status_code=404, detail="Conta não encontrada")
    db_conta.nome = conta_update.nome
    db_conta.tipo = conta_update.tipo
    db_conta.dia_fechamento = conta_update.dia_fechamento
    db_conta.dia_vencimento = conta_update.dia_vencimento
    db.commit()
    db.refresh(db_conta)
    return db_conta

@router.delete("/{conta_id}", status_code=204)
def delete_conta(
    conta_id: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    """
    Remove uma conta do usuário autenticado.
    """
    db_conta = db.query(models.Conta).filter(
        models.Conta.id == conta_id,
        models.Conta.id_usuario == current_user.id
    ).first()
    if db_conta is None:
        raise HTTPException(status_code=404, detail="Conta não encontrada")
    db.delete(db_conta)
    db.commit()
    return None
