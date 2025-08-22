from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..core.database import get_db, listar_objetivos_usuario
from ..models import schemas, models
from .auth import get_current_user

router = APIRouter(prefix="/metas", tags=["Metas e Objetivos"])

@router.get("/", response_model=List[schemas.Objetivo])
def read_user_metas(
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    """
    Lista todas as metas do usuário logado.
    Esta função REUTILIZA sua lógica de `listar_objetivos_usuario`.
    """
    # A função do database.py esperava um telegram_id, vamos adaptar para usar o id do usuário
    # (Ou você pode adaptar a função listar_objetivos_usuario para aceitar o objeto do usuário)
    
    # Adaptação rápida aqui:
    objetivos = db.query(models.Objetivo).filter(models.Objetivo.id_usuario == current_user.id).all()
    
    return objetivos

@router.post("/", response_model=schemas.Objetivo, status_code=201)
def create_meta(
    meta: schemas.ObjetivoBase,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    """
    Cria uma nova meta para o usuário autenticado.
    """
    nova_meta = models.Objetivo(
        descricao=meta.descricao,
        valor_meta=meta.valor_meta,
        data_meta=meta.data_meta,
        id_usuario=current_user.id
    )
    db.add(nova_meta)
    db.commit()
    db.refresh(nova_meta)
    return nova_meta

@router.put("/{meta_id}", response_model=schemas.Objetivo)
def update_meta(
    meta_id: int,
    meta_update: schemas.ObjetivoBase,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    """
    Atualiza uma meta existente do usuário autenticado.
    """
    db_meta = db.query(models.Objetivo).filter(
        models.Objetivo.id == meta_id,
        models.Objetivo.id_usuario == current_user.id
    ).first()
    if db_meta is None:
        raise HTTPException(status_code=404, detail="Meta não encontrada")
    db_meta.descricao = meta_update.descricao
    db_meta.valor_meta = meta_update.valor_meta
    db_meta.data_meta = meta_update.data_meta
    db.commit()
    db.refresh(db_meta)
    return db_meta

@router.delete("/{meta_id}", status_code=204)
def delete_meta(
    meta_id: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    """
    Remove uma meta do usuário autenticado.
    """
    db_meta = db.query(models.Objetivo).filter(
        models.Objetivo.id == meta_id,
        models.Objetivo.id_usuario == current_user.id
    ).first()
    if db_meta is None:
        raise HTTPException(status_code=404, detail="Meta não encontrada")
    db.delete(db_meta)
    db.commit()
    return None