# app/models/schemas.py
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import date, datetime

# --- Schemas de Usuário e Token ---
class UserBase(BaseModel):
    email: EmailStr
    nome_completo: Optional[str] = None

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    telegram_id: Optional[int] = None # Mantemos para possível integração futura

    class Config:
        from_attributes = True # Permite mapear de modelos SQLAlchemy

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

# --- Schemas de Metas (para o Passo 5) ---
class ObjetivoBase(BaseModel):
    descricao: str
    valor_meta: float
    data_meta: date

class Objetivo(ObjetivoBase):
    id: int
    valor_atual: float
    criado_em: datetime

    class Config:
        from_attributes = True


class LancamentoBase(BaseModel):
    descricao: str
    valor: float
    tipo: str  # "Entrada" ou "Saída"
    data_transacao: datetime
    forma_pagamento: Optional[str] = None
    id_conta: Optional[int] = None
    id_categoria: Optional[int] = None
    id_subcategoria: Optional[int] = None

class LancamentoCreateFrontend(BaseModel):
    descricao: str
    valor: float
    tipo: str  # "receita" ou "despesa" (formato do frontend)
    data_transacao: datetime
    categoria: str
    forma_pagamento: Optional[str] = None
    id_conta: Optional[int] = None

class LancamentoCreate(LancamentoBase):
    pass

class LancamentoUpdate(BaseModel):
    descricao: Optional[str] = None
    valor: Optional[float] = None
    data_transacao: Optional[datetime] = None
    id_conta: Optional[int] = None
    id_categoria: Optional[int] = None
    id_subcategoria: Optional[int] = None

class Lancamento(LancamentoBase):
    id: int
    id_usuario: int

    class Config:
        from_attributes = True


class ContaBase(BaseModel):
    nome: str
    tipo: str
    dia_fechamento: Optional[int] = None
    dia_vencimento: Optional[int] = None

class ContaCreate(ContaBase):
    pass

class Conta(ContaBase):
    id: int
    id_usuario: int

    class Config:
        from_attributes = True


class CategoriaBase(BaseModel):
    nome: str

class CategoriaCreate(CategoriaBase):
    pass

class Categoria(CategoriaBase):
    id: int
    class Config:
        from_attributes = True

class SubcategoriaBase(BaseModel):
    nome: str
    id_categoria: int

class SubcategoriaCreate(SubcategoriaBase):
    pass

class Subcategoria(SubcategoriaBase):
    id: int
    class Config:
        from_attributes = True


class AgendamentoBase(BaseModel):
    descricao: str
    valor: float
    tipo: str
    id_categoria: Optional[int] = None
    id_subcategoria: Optional[int] = None
    data_primeiro_evento: date
    frequencia: str
    total_parcelas: Optional[int] = None
    parcela_atual: Optional[int] = 0
    proxima_data_execucao: date
    ativo: Optional[bool] = True

class AgendamentoCreate(AgendamentoBase):
    pass

class AgendamentoUpdate(BaseModel):
    descricao: Optional[str] = None
    valor: Optional[float] = None
    tipo: Optional[str] = None
    id_categoria: Optional[int] = None
    id_subcategoria: Optional[int] = None
    data_primeiro_evento: Optional[date] = None
    frequencia: Optional[str] = None
    total_parcelas: Optional[int] = None
    parcela_atual: Optional[int] = None
    proxima_data_execucao: Optional[date] = None
    ativo: Optional[bool] = None

class Agendamento(AgendamentoBase):
    id: int
    id_usuario: int
    criado_em: datetime

    class Config:
        from_attributes = True

# --- Schemas de Chat ---
class ChatMessage(BaseModel):
    content: str

class ChatResponse(BaseModel):
    content: str
    type: str  # "text", "action", "visualization"
    suggestions: List[str] = []
    actions: List[Dict[str, Any]] = []

class ChatHistoryResponse(BaseModel):
    id: int
    user_message: str
    ai_response: str
    created_at: datetime

    class Config:
        from_attributes = True

# --- Schemas de Dashboard ---
class TransactionSummary(BaseModel):
    id: int
    description: str
    amount: float
    type: str
    date: datetime
    category: Optional[str] = None

class DashboardOverview(BaseModel):
    total_balance: float
    monthly_expenses: float
    monthly_income: float
    monthly_balance: float
    active_goals: int
    avg_goal_progress: float
    recent_transactions: List[TransactionSummary]