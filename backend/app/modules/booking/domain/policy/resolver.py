"""
Resolver de políticas de booking por tenant (FIX-CONFIG-01).

Precedência: override ativo da empresa → defaults de instalação → fallback seguro.
"""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.modules.booking.domain.policy.defaults import (
    get_installation_defaults,
    get_safe_fallback_policy,
)
from app.modules.booking.domain.policy.models import BookingPolicyConfig
from app.modules.booking.domain.policy.schemas import BookingPolicy
from app.modules.booking.domain.policy.validation import merge_and_validate

logger = logging.getLogger(__name__)


class BookingPolicyResolver:
    """
    Resolve a política efetiva de booking para um ``company_id``.

    Sem override ativo, retorna defaults de instalação.
    Override inválido ou erro de leitura → fallback seguro + log (fail-closed).
    """

    def __init__(self, db: Session) -> None:
        """
        Inicializa o resolver com sessão de banco.

        Args:
            db: Sessão SQLAlchemy.
        """
        self._db = db

    def get_installation_defaults(self) -> BookingPolicy:
        """
        Expõe os defaults de instalação (sem consultar banco).

        Returns:
            Política padrão imutável.
        """
        return get_installation_defaults()

    def resolve(self, company_id: int) -> BookingPolicy:
        """
        Resolve a política efetiva para o tenant.

        Args:
            company_id: Identificador da empresa (obrigatório).

        Returns:
            ``BookingPolicy`` efetiva (defaults, override mesclado ou fallback).

        Raises:
            ValueError: Se ``company_id`` for None ou não-int positivo.
        """
        if company_id is None:
            raise ValueError("company_id é obrigatório para resolver política de booking")
        if not isinstance(company_id, int) or isinstance(company_id, bool):
            raise ValueError("company_id deve ser int")
        if company_id <= 0:
            raise ValueError("company_id deve ser positivo")

        try:
            row = (
                self._db.query(BookingPolicyConfig)
                .filter(
                    BookingPolicyConfig.company_id == company_id,
                    BookingPolicyConfig.is_active.is_(True),
                )
                .first()
            )
        except Exception:
            logger.exception(
                "booking_policy_resolve_db_error company_id=%s",
                company_id,
            )
            return get_safe_fallback_policy()

        if row is None:
            return get_installation_defaults()

        override = row.policy_json if isinstance(row.policy_json, dict) else None
        if override is None:
            logger.warning(
                "booking_policy_invalid_json company_id=%s version=%s",
                company_id,
                getattr(row, "version", None),
            )
            return get_safe_fallback_policy()

        policy, error = merge_and_validate(override)
        if error or policy is None:
            logger.warning(
                "booking_policy_invalid_override company_id=%s version=%s error=%s",
                company_id,
                getattr(row, "version", None),
                error,
            )
            return get_safe_fallback_policy()

        return policy

    def resolve_optional(self, company_id: Optional[int]) -> BookingPolicy:
        """
        Variante que exige company_id e falha explicitamente se ausente.

        Args:
            company_id: Identificador ou None.

        Returns:
            Política efetiva.

        Raises:
            ValueError: Se company_id for None.
        """
        if company_id is None:
            raise ValueError("company_id é obrigatório para resolver política de booking")
        return self.resolve(company_id)
