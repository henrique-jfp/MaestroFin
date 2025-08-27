#!/usr/bin/env python3
"""
🔧 DATABASE ULTRA-ROBUSTA - Com Timeout e Skip Automático
"""

import logging
import signal
import os
from contextlib import contextmanager

logger = logging.getLogger(__name__)

@contextmanager
def timeout_context(seconds):
    """Context manager para timeout em operações de banco"""
    def timeout_handler(signum, frame):
        raise TimeoutError(f"Operação expirou após {seconds} segundos")
    
    # Configurar handler de timeout
    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)
    
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)

def popular_dados_iniciais_ultra_robusta(db_session):
    """
    🔥 VERSÃO ULTRA-ROBUSTA - População de dados com timeout
    """
    try:
        logger.info("🔧 [ULTRA-ROBUST] Iniciando população de dados com timeout...")
        
        # ⏰ TIMEOUT DE 30 SEGUNDOS - SKIP SE TRAVAR
        with timeout_context(30):
            from sqlalchemy import func, and_
            from models import Categoria, Subcategoria
            
            logger.info("📦 Verificando categorias existentes...")
            
            # 🔥 VERIFICAÇÃO RÁPIDA - SE JÁ EXISTEM, SKIP
            count_categorias = db_session.query(Categoria).count()
            if count_categorias >= 10:  # Threshold mínimo
                logger.info(f"✅ [SKIP] {count_categorias} categorias já existem - pulando população")
                return True
            
            # 🏭 POPULAÇÃO MÍNIMA E RÁPIDA
            categorias_essenciais = {
                "Alimentação": ["Supermercado", "Restaurante"],
                "Transporte": ["Combustível", "App Transporte"],
                "Saúde": ["Farmácia", "Consulta"],
                "Receitas": ["Salário", "Freelance"],
                "Outros": ["Diversos"]
            }
            
            logger.info("🏭 Populando categorias essenciais...")
            
            for nome_cat, subs in categorias_essenciais.items():
                try:
                    # Categoria
                    categoria_obj = db_session.query(Categoria).filter(
                        func.lower(Categoria.nome) == func.lower(nome_cat)
                    ).first()
                    
                    if not categoria_obj:
                        categoria_obj = Categoria(nome=nome_cat)
                        db_session.add(categoria_obj)
                        db_session.flush()  # Flush sem commit
                        logger.info(f"📂 Categoria '{nome_cat}' criada")
                    
                    # Subcategorias
                    for nome_sub in subs:
                        subcategoria_obj = db_session.query(Subcategoria).filter(
                            and_(
                                Subcategoria.id_categoria == categoria_obj.id,
                                func.lower(Subcategoria.nome) == func.lower(nome_sub)
                            )
                        ).first()
                        
                        if not subcategoria_obj:
                            nova_sub = Subcategoria(nome=nome_sub, id_categoria=categoria_obj.id)
                            db_session.add(nova_sub)
                            logger.info(f"📋 Subcategoria '{nome_sub}' criada")
                
                except Exception as cat_error:
                    logger.warning(f"⚠️ Erro ao criar categoria '{nome_cat}': {cat_error}")
                    continue
            
            # 🔥 COMMIT ÚNICO E RÁPIDO
            db_session.commit()
            logger.info("✅ [ULTRA-ROBUST] População concluída com sucesso!")
            return True
            
    except TimeoutError:
        logger.warning("⏰ [TIMEOUT] População de dados expirou - continuando sem dados iniciais")
        try:
            db_session.rollback()
        except:
            pass
        return False
        
    except Exception as e:
        logger.error(f"❌ [ULTRA-ROBUST] Erro na população: {e}")
        try:
            db_session.rollback()
        except:
            pass
        return False

def verificar_e_popular_se_necessario(db_session):
    """
    🎯 FUNÇÃO WRAPPER - Só popula se realmente necessário
    """
    try:
        # 🔍 VERIFICAÇÃO ULTRA-RÁPIDA
        from models import Categoria
        total_cats = db_session.query(Categoria).count()
        
        if total_cats == 0:
            logger.info("🔧 Banco vazio - populando dados essenciais...")
            return popular_dados_iniciais_ultra_robusta(db_session)
        else:
            logger.info(f"✅ Banco já populado ({total_cats} categorias) - skip")
            return True
            
    except Exception as e:
        logger.warning(f"⚠️ Erro na verificação: {e} - continuando sem população")
        return False
