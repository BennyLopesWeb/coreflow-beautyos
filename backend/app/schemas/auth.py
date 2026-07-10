"""
Schemas de Autenticação
DTOs para login, registro, tokens
"""
from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime
import re


class UserBase(BaseModel):
    """Schema base de usuário"""
    email: str
    nome: str
    telefone: Optional[str] = None
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        """Valida formato de email"""
        if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', v):
            raise ValueError('Email inválido')
        return v.lower()


class UserCreate(UserBase):
    """Schema para criação de usuário"""
    password: str
    telefone: str

    @field_validator('telefone')
    @classmethod
    def validate_telefone(cls, v):
        """Valida telefone obrigatório com mínimo de dígitos."""
        digits = re.sub(r'\D', '', v or '')
        if len(digits) < 10:
            raise ValueError('Telefone inválido (mínimo 10 dígitos)')
        return v.strip()
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        """Valida senha (mínimo 6 caracteres)"""
        if len(v) < 6:
            raise ValueError('Senha deve ter no mínimo 6 caracteres')
        return v


class UserResponse(UserBase):
    """Schema de resposta de usuário"""
    id: int
    ativo: bool
    is_superuser: bool = False
    created_at: datetime
    
    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    """Schema para login"""
    email: str
    password: str
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        """Valida formato de email"""
        if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', v):
            raise ValueError('Email inválido')
        return v.lower()


class TokenResponse(BaseModel):
    """Schema de resposta de token"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    """Schema para refresh token"""
    refresh_token: str


class TokenData(BaseModel):
    """Dados do token decodificado"""
    user_id: Optional[int] = None
    email: Optional[str] = None

