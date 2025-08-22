# app/api/chat.py
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from sqlalchemy import and_, extract, func

from ..core.database import get_db
from ..models import schemas, models
from .auth import get_current_user
from ..services.ai_service import GerenteFinanceiroAI

router = APIRouter(prefix="/chat", tags=["Chat IA"])

# Instância do gerente financeiro com IA
gerente_ai = GerenteFinanceiroAI()

@router.post("/", response_model=schemas.ChatResponse)
async def send_message(
    message: schemas.ChatMessage,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    """
    Envia uma mensagem para o gerente financeiro IA e recebe uma resposta.
    """
    try:
        # Busca contexto financeiro do usuário
        context = await _get_user_financial_context(db, current_user.id)
        
        # Processa a mensagem com IA
        ai_response = await gerente_ai.process_message(
            message.content,
            context=context,
            user_id=current_user.id
        )
        
        # Salva a conversa no banco
        chat_entry = models.ChatHistory(
            id_usuario=current_user.id,
            user_message=message.content,
            ai_response=ai_response.content,
            created_at=datetime.now()
        )
        db.add(chat_entry)
        db.commit()
        
        return schemas.ChatResponse(
            content=ai_response.content,
            type=ai_response.type,
            suggestions=ai_response.suggestions,
            actions=ai_response.actions
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar mensagem: {str(e)}")

@router.get("/history", response_model=List[schemas.ChatHistoryResponse])
def get_chat_history(
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    """
    Recupera o histórico de conversas do usuário.
    """
    history = db.query(models.ChatHistory).filter(
        models.ChatHistory.id_usuario == current_user.id
    ).order_by(models.ChatHistory.created_at.desc()).limit(limit).all()
    
    return [
        schemas.ChatHistoryResponse(
            id=chat.id,
            user_message=chat.user_message,
            ai_response=chat.ai_response,
            created_at=chat.created_at
        )
        for chat in history
    ]

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    db: Session = Depends(get_db)
):
    """
    WebSocket para chat em tempo real.
    """
    await websocket.accept()
    
    try:
        while True:
            # Recebe mensagem do cliente
            data = await websocket.receive_json()
            message = data.get("message")
            user_id = data.get("user_id")  # Em produção, validar via token
            
            if not message or not user_id:
                await websocket.send_json({"error": "Mensagem ou usuário inválido"})
                continue
            
            # Busca contexto do usuário
            context = await _get_user_financial_context(db, user_id)
            
            # Processa com IA
            ai_response = await gerente_ai.process_message(
                message,
                context=context,
                user_id=user_id
            )
            
            # Envia resposta
            await websocket.send_json({
                "content": ai_response.content,
                "type": ai_response.type,
                "suggestions": ai_response.suggestions,
                "actions": ai_response.actions,
                "timestamp": datetime.now().isoformat()
            })
            
    except WebSocketDisconnect:
        pass

async def _get_user_financial_context(db: Session, user_id: int) -> Dict[str, Any]:
    """
    Busca contexto financeiro do usuário para alimentar a IA.
    """
    # Lançamentos recentes
    recent_launches = db.query(models.Lancamento).filter(
        models.Lancamento.id_usuario == user_id,
        models.Lancamento.data_transacao >= datetime.now() - timedelta(days=30)
    ).all()
    
    # Metas
    goals = db.query(models.Objetivo).filter(
        models.Objetivo.id_usuario == user_id
    ).all()
    
    # Contas
    accounts = db.query(models.Conta).filter(
        models.Conta.id_usuario == user_id
    ).all()
    
    # Categorias mais usadas
    top_categories = db.query(
        models.Categoria.nome,
        func.count(models.Lancamento.id).label('count')
    ).join(models.Lancamento).filter(
        models.Lancamento.id_usuario == user_id
    ).group_by(models.Categoria.nome).order_by(func.count(models.Lancamento.id).desc()).limit(5).all()
    
    # Resumo mensal
    current_month = datetime.now().month
    current_year = datetime.now().year
    
    monthly_summary = db.query(
        func.sum(models.Lancamento.valor).label('total'),
        models.Lancamento.tipo
    ).filter(
        models.Lancamento.id_usuario == user_id,
        extract('month', models.Lancamento.data_transacao) == current_month,
        extract('year', models.Lancamento.data_transacao) == current_year
    ).group_by(models.Lancamento.tipo).all()
    
    return {
        'recent_launches': [
            {
                'descricao': l.descricao,
                'valor': float(l.valor),
                'tipo': l.tipo,
                'data': l.data_transacao.isoformat()
            }
            for l in recent_launches
        ],
        'goals': [
            {
                'descricao': g.descricao,
                'valor_meta': float(g.valor_meta),
                'valor_atual': float(g.valor_atual),
                'progresso': (float(g.valor_atual) / float(g.valor_meta)) * 100
            }
            for g in goals
        ],
        'accounts': [
            {
                'nome': a.nome,
                'saldo': float(a.saldo),
                'tipo': a.tipo
            }
            for a in accounts
        ],
        'top_categories': [
            {
                'nome': cat.nome,
                'count': cat.count
            }
            for cat in top_categories
        ],
        'monthly_summary': {
            summary.tipo: float(summary.total or 0)
            for summary in monthly_summary
        }
    }
