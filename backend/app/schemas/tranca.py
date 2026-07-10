"""
Schemas de Tranca (categoria)
A categoria agrupa modelos — sem preço, duração ou sinal.
"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


class TrancaBase(BaseModel):
    """Schema base de categoria de trança (apenas organização)."""
    nome: str
    descricao: Optional[str] = None
    imagens: List[str] = []
    ativo: bool = True


class TrancaCreate(TrancaBase):
    """Schema para criação de categoria."""
    pass


class TrancaUpdate(BaseModel):
    """Schema para atualização de categoria."""
    nome: Optional[str] = None
    descricao: Optional[str] = None
    imagens: Optional[List[str]] = None
    ativo: Optional[bool] = None


class TrancaImagensUpdate(BaseModel):
    """Schema para definir galeria completa de imagens de capa."""
    imagens: List[str]


class TrancaResponse(TrancaBase):
    """Schema de resposta de categoria."""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
