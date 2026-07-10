"""
Schemas de Company (tenant BeautyOS).
"""
from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime
import re

from app.models.company import CompanySegment, CompanyPlan
from app.models.user_company import CompanyRole


class CompanyBase(BaseModel):
    """Campos base de uma empresa."""

    nome: str
    slug: str
    segmento: CompanySegment = CompanySegment.TRANCISTA
    timezone: str = "America/Sao_Paulo"
    logo_url: Optional[str] = None

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, value: str) -> str:
        """
        Valida slug URL-safe.

        Args:
            value: Slug informado.

        Returns:
            Slug normalizado em minúsculas.
        """
        slug = value.strip().lower()
        if not re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", slug):
            raise ValueError("Slug inválido (use letras, números e hífens)")
        return slug


class CompanyCreate(CompanyBase):
    """Schema para criação de empresa."""

    plano: CompanyPlan = CompanyPlan.FREE


class CompanyResponse(CompanyBase):
    """Resposta pública de empresa."""

    id: int
    plano: CompanyPlan
    plugin_id: str = "beauty"
    ativo: bool
    created_at: datetime

    class Config:
        from_attributes = True


class CompanyMembershipResponse(BaseModel):
    """Vínculo usuário ↔ empresa exposto na API."""

    company_id: int
    company_nome: str
    company_slug: str
    role: CompanyRole

    class Config:
        from_attributes = True


class UserMeResponse(BaseModel):
    """Perfil do usuário autenticado com contexto de tenant."""

    id: int
    email: str
    nome: str
    telefone: Optional[str] = None
    ativo: bool
    is_superuser: bool = False
    company_id: Optional[int] = None
    company_slug: Optional[str] = None
    role: Optional[CompanyRole] = None
    created_at: datetime

    class Config:
        from_attributes = True
