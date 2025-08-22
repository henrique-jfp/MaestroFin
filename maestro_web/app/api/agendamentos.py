from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..models import models, schemas
from .auth import get_current_user

router = APIRouter(prefix="/agendamentos", tags=["Agendamentos"])

@router.get("/", response_model=List[schemas.Agendamento])
def read_agendamentos(
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    agendamentos = db.query(models.Agendamento).filter(models.Agendamento.id_usuario == current_user.id).all()
    return agendamentos

@router.post("/", response_model=schemas.Agendamento, status_code=201)
def create_agendamento(
    agendamento: schemas.AgendamentoCreate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    novo_agendamento = models.Agendamento(
        descricao=agendamento.descricao,
        valor=agendamento.valor,
        tipo=agendamento.tipo,
        id_categoria=agendamento.id_categoria,
        id_subcategoria=agendamento.id_subcategoria,
        data_primeiro_evento=agendamento.data_primeiro_evento,
        frequencia=agendamento.frequencia,
        total_parcelas=agendamento.total_parcelas,
        parcela_atual=agendamento.parcela_atual,
        proxima_data_execucao=agendamento.proxima_data_execucao,
        ativo=agendamento.ativo,
        id_usuario=current_user.id
    )
    db.add(novo_agendamento)
    db.commit()
    db.refresh(novo_agendamento)
    return novo_agendamento

@router.put("/{agendamento_id}", response_model=schemas.Agendamento)
def update_agendamento(
    agendamento_id: int,
    agendamento_update: schemas.AgendamentoUpdate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    db_agendamento = db.query(models.Agendamento).filter(
        models.Agendamento.id == agendamento_id,
        models.Agendamento.id_usuario == current_user.id
    ).first()
    if db_agendamento is None:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")
    update_data = agendamento_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_agendamento, key, value)
    db.commit()
    db.refresh(db_agendamento)
    return db_agendamento

@router.delete("/{agendamento_id}", status_code=204)
def delete_agendamento(
    agendamento_id: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    db_agendamento = db.query(models.Agendamento).filter(
        models.Agendamento.id == agendamento_id,
        models.Agendamento.id_usuario == current_user.id
    ).first()
    if db_agendamento is None:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")
    db.delete(db_agendamento)
    db.commit()
    return None
