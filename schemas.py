
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, Field

class TransactionSchema(BaseModel):
    """Representa uma única transação financeira para lógica de negócio."""
    id: int
    description: str
    amount: Decimal = Field(..., description="Valor da transação. Positivo para receitas, negativo para despesas.")
    category: Optional[str] = None
    date: datetime
    
    class Config:
        orm_mode = True # Permite criar este schema a partir de um modelo SQLAlchemy

class FinancialReportSchema(BaseModel):
    """Agrega o contexto financeiro completo de um usuário para análise."""
    user_name: str
    transactions: List[TransactionSchema]
    total_income: Decimal = Field(Decimal(0), description="Soma de todas as receitas no período.")
    total_expense: Decimal = Field(Decimal(0), description="Soma de todas as despesas no período.")
    
    @property
    def balance(self) -> Decimal:
        """Calcula o saldo do período."""
        return self.total_income - self.total_expense
    
    @property
    def top_expense_category(self) -> Optional[str]:
        """Calcula a categoria com a maior despesa."""
        if not self.transactions:
            return None
        
        expenses_by_category = {}
        for t in self.transactions:
            if t.amount < 0 and t.category:
                expenses_by_category[t.category] = expenses_by_category.get(t.category, Decimal(0)) + abs(t.amount)
        
        if not expenses_by_category:
            return None
            
        return max(expenses_by_category, key=expenses_by_category.get)

class PromptContext(BaseModel):
    """
    Contém todos os dados e serviços necessários para a execução de um prompt.
    Este objeto é o 'mundo' que o prompt conhece.
    """
    user_id: int
    financial_report: Optional[FinancialReportSchema] = None
    # No futuro, podemos adicionar mais dependências aqui:
    # db_session: Any 
    # llm_client: Any
    # etc...
