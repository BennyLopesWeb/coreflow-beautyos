"""
Schemas de Financeiro
DTOs para validação e serialização de movimentações financeiras
"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from decimal import Decimal
from app.models.financeiro import TipoMovimento


class FinanceiroBase(BaseModel):
    """Schema base de movimento financeiro"""
    tipo: TipoMovimento
    descricao: str
    valor: Decimal
    data: datetime


class FinanceiroCreate(FinanceiroBase):
    """Schema para criação de movimento financeiro"""
    agendamento_id: Optional[int] = None


class SaidaCreate(BaseModel):
    """Schema para criação de saída manual"""
    descricao: str
    valor: Decimal
    data: Optional[datetime] = None


class FinanceiroResponse(FinanceiroBase):
    """Schema de resposta de movimento financeiro"""
    id: int
    agendamento_id: Optional[int] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class ResumoFinanceiroResponse(BaseModel):
    """Schema de resumo financeiro"""
    inicio: datetime
    fim: datetime
    total_entradas: Decimal
    total_saidas: Decimal
    saldo: Decimal
    movimentos: List[FinanceiroResponse] = []

