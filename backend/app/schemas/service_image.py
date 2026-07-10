"""
Schemas de modelos de trança (fotos com preço individual).
"""
from pydantic import BaseModel, field_validator
from decimal import Decimal
from typing import Optional


def _label_modelo(img) -> str:
    """
    Retorna nome de exibição do modelo.

    Args:
        img: Instância ServiceImage.

    Returns:
        Nome do modelo ou fallback "Modelo N".
    """
    if img.nome and str(img.nome).strip():
        return str(img.nome).strip()
    return f"Modelo {img.ordem}"


class TrancaImagemResponse(BaseModel):
    """Modelo de trança com preço, duração e metadados próprios."""
    id: int
    url: str
    ordem: int
    is_principal: bool
    nome: str
    descricao: Optional[str] = None
    nivel_complexidade: Optional[str] = None
    quantidade_trancas: Optional[int] = None
    quantidade_cabelo: Optional[str] = None
    ativo: bool = True
    label: str
    valor_total: Decimal
    valor_sinal: Decimal
    valor_restante: Decimal
    duracao_minutos: int
    percentual_sinal: Decimal = Decimal("0.30")

    class Config:
        from_attributes = True

    @classmethod
    def from_model(
        cls,
        img,
        tranca=None,
        *,
        exigir_precos: bool = True,
    ) -> "TrancaImagemResponse":
        """
        Constrói resposta a partir do model ServiceImage.

        Args:
            img: Instância ServiceImage.
            tranca: Ignorado.
            exigir_precos: Se False, permite modelo sem preço (admin).

        Returns:
            TrancaImagemResponse.
        """
        from app.utils.service_image_precos import (
            resolver_precos_imagem,
            PERCENTUAL_SINAL_PADRAO,
            calcular_sinal,
        )

        nome = _label_modelo(img)
        try:
            precos = resolver_precos_imagem(img)
        except ValueError:
            if exigir_precos:
                raise
            pct = img.percentual_sinal or PERCENTUAL_SINAL_PADRAO
            total = img.valor_total or Decimal("0")
            sinal = calcular_sinal(Decimal(str(total)), Decimal(str(pct))) if total else Decimal("0")
            precos = {
                "valor_total": total,
                "valor_sinal": sinal,
                "valor_restante": total - sinal,
                "duracao_minutos": img.duracao_minutos or 0,
                "percentual_sinal": Decimal(str(pct)),
            }

        return cls(
            id=img.id,
            url=img.url,
            ordem=img.ordem,
            is_principal=img.is_principal,
            nome=nome,
            descricao=img.descricao,
            nivel_complexidade=img.nivel_complexidade,
            quantidade_trancas=img.quantidade_trancas,
            quantidade_cabelo=img.quantidade_cabelo,
            ativo=bool(img.ativo) if img.ativo is not None else True,
            label=nome,
            valor_total=precos["valor_total"],
            valor_sinal=precos["valor_sinal"],
            valor_restante=precos["valor_restante"],
            duracao_minutos=precos["duracao_minutos"],
            percentual_sinal=precos["percentual_sinal"],
        )


class TrancaImagemUpdate(BaseModel):
    """Atualização comercial e descritiva de um modelo."""
    nome: Optional[str] = None
    descricao: Optional[str] = None
    nivel_complexidade: Optional[str] = None
    quantidade_trancas: Optional[int] = None
    quantidade_cabelo: Optional[str] = None
    valor_total: Optional[Decimal] = None
    duracao_minutos: Optional[int] = None
    percentual_sinal: Optional[Decimal] = None
    ativo: Optional[bool] = None

    @field_validator("duracao_minutos")
    @classmethod
    def duracao_positiva(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v <= 0:
            raise ValueError("Duração deve ser maior que zero")
        return v

    @field_validator("percentual_sinal")
    @classmethod
    def percentual_valido(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and (v <= 0 or v > 1):
            raise ValueError("Percentual de sinal deve estar entre 0 e 1 (ex: 0.30)")
        return v

    @field_validator("nivel_complexidade")
    @classmethod
    def complexidade_valida(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        permitidos = {"baixa", "media", "alta"}
        normalizado = v.strip().lower()
        if normalizado not in permitidos:
            raise ValueError("Complexidade deve ser: baixa, media ou alta")
        return normalizado
