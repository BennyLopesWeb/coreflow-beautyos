"""
Schemas de Cliente
DTOs para validação e serialização de clientes
"""
from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Optional
import re


class ClienteBase(BaseModel):
    """Schema base de cliente"""
    nome: str
    telefone: str
    email: Optional[str] = None
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        """Valida formato de email se fornecido"""
        if v and not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', v):
            raise ValueError('Email inválido')
        return v


class ClienteCreate(ClienteBase):
    """Schema para criação de cliente"""
    pass


class ClienteUpdate(BaseModel):
    """Schema para atualização de cliente"""
    nome: Optional[str] = None
    telefone: Optional[str] = None
    email: Optional[str] = None
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        """Valida formato de email se fornecido"""
        if v and not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', v):
            raise ValueError('Email inválido')
        return v


class ClienteResponse(ClienteBase):
    """Schema de resposta de cliente"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

