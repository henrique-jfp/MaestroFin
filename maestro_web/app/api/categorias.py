from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..models import models, schemas
from .auth import get_current_user

router = APIRouter(prefix="/categorias", tags=["Categorias"])

@router.get("/", response_model=List[schemas.Categoria])
def read_categorias(
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    categorias = db.query(models.Categoria).all()
    return categorias

@router.post("/", response_model=schemas.Categoria, status_code=201)
def create_categoria(
    categoria: schemas.CategoriaCreate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    nova_categoria = models.Categoria(nome=categoria.nome)
    db.add(nova_categoria)
    db.commit()
    db.refresh(nova_categoria)
    return nova_categoria

@router.put("/{categoria_id}", response_model=schemas.Categoria)
def update_categoria(
    categoria_id: int,
    categoria_update: schemas.CategoriaCreate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    db_categoria = db.query(models.Categoria).filter(models.Categoria.id == categoria_id).first()
    if db_categoria is None:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    db_categoria.nome = categoria_update.nome
    db.commit()
    db.refresh(db_categoria)
    return db_categoria

@router.delete("/{categoria_id}", status_code=204)
def delete_categoria(
    categoria_id: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    db_categoria = db.query(models.Categoria).filter(models.Categoria.id == categoria_id).first()
    if db_categoria is None:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    db.delete(db_categoria)
    db.commit()
    return None

# SUBCATEGORIAS

@router.get("/{categoria_id}/subcategorias", response_model=List[schemas.Subcategoria])
def read_subcategorias(
    categoria_id: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    subcategorias = db.query(models.Subcategoria).filter(models.Subcategoria.id_categoria == categoria_id).all()
    return subcategorias

@router.post("/{categoria_id}/subcategorias", response_model=schemas.Subcategoria, status_code=201)
def create_subcategoria(
    categoria_id: int,
    subcategoria: schemas.SubcategoriaCreate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    nova_subcategoria = models.Subcategoria(
        nome=subcategoria.nome,
        id_categoria=categoria_id
    )
    db.add(nova_subcategoria)
    db.commit()
    db.refresh(nova_subcategoria)
    return nova_subcategoria

@router.put("/subcategorias/{subcategoria_id}", response_model=schemas.Subcategoria)
def update_subcategoria(
    subcategoria_id: int,
    subcategoria_update: schemas.SubcategoriaCreate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    db_subcategoria = db.query(models.Subcategoria).filter(models.Subcategoria.id == subcategoria_id).first()
    if db_subcategoria is None:
        raise HTTPException(status_code=404, detail="Subcategoria não encontrada")
    db_subcategoria.nome = subcategoria_update.nome
    db_subcategoria.id_categoria = subcategoria_update.id_categoria
    db.commit()
    db.refresh(db_subcategoria)
    return db_subcategoria

@router.delete("/subcategorias/{subcategoria_id}", status_code=204)
def delete_subcategoria(
    subcategoria_id: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    db_subcategoria = db.query(models.Subcategoria).filter(models.Subcategoria.id == subcategoria_id).first()
    if db_subcategoria is None:
        raise HTTPException(status_code=404, detail="Subcategoria não encontrada")
    db.delete(db_subcategoria)
    db.commit()
    return None
