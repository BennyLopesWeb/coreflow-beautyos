"""
Service fino da API administrativa de política de booking (FIX-CONFIG-02).

Persiste overrides por tenant, valida via ``merge_and_validate`` e audita
com ``record_policy_change``. Não altera consumidores runtime (expiração,
cancelamento, PATCH) — apenas a superfície de configuração.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any, Dict, Mapping, Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, ValidationError
from app.modules.booking.domain.policy.audit import record_policy_change
from app.modules.booking.domain.policy.models import BookingPolicyConfig
from app.modules.booking.domain.policy.resolver import BookingPolicyResolver
from app.modules.booking.domain.policy.validation import deep_merge, merge_and_validate
from app.schemas.booking_policy_admin import BookingPolicyAdminResponse


class BookingPolicyAdminService:
    """
    Operações tenant-scoped sobre ``BookingPolicyConfig``.

    Args:
        db: Sessão SQLAlchemy da requisição.
    """

    def __init__(self, db: Session) -> None:
        """
        Inicializa o service.

        Args:
            db: Sessão SQLAlchemy.
        """
        self.db = db

    def get_policy(self, company_id: int) -> BookingPolicyAdminResponse:
        """
        Retorna a política efetiva do tenant e metadados do override ativo.

        Args:
            company_id: Tenant efetivo autenticado.

        Returns:
            Resposta com política resolvida e override (se ativo).

        Raises:
            ValueError: ``company_id`` inválido.
        """
        self._require_company_id(company_id)
        resolver = BookingPolicyResolver(self.db)
        effective = resolver.resolve(company_id)
        row = self._get_active_row(company_id)
        if row is None:
            return BookingPolicyAdminResponse(
                company_id=company_id,
                has_active_override=False,
                source="default",
                policy=effective.to_public_dict(),
                override=None,
                version=None,
                updated_at=None,
            )
        override = dict(row.policy_json) if isinstance(row.policy_json, dict) else {}
        return BookingPolicyAdminResponse(
            company_id=company_id,
            has_active_override=True,
            source="override",
            policy=effective.to_public_dict(),
            override=override,
            version=row.version,
            updated_at=row.updated_at,
        )

    def put_override(
        self,
        company_id: int,
        override: Mapping[str, Any],
        *,
        actor_user_id: Optional[int],
        reason: Optional[str] = None,
        expected_version: Optional[int] = None,
    ) -> BookingPolicyAdminResponse:
        """
        Substitui o documento de override do tenant (semântica PUT).

        O body torna-se o novo ``policy_json`` (após validação). Campos não
        enviados deixam de fazer parte do override e voltam ao default na
        resolução efetiva.

        Args:
            company_id: Tenant efetivo.
            override: Documento de override (parcial ou completo).
            actor_user_id: Usuário autenticado.
            reason: Motivo opcional de auditoria.

        Returns:
            Política efetiva após persistência.

        Raises:
            ValidationError: Payload inválido.
            ConflictError: Conflito de unicidade no banco.
            ValueError: ``company_id`` inválido.
        """
        return self._upsert_override(
            company_id,
            override,
            merge_with_existing=False,
            actor_user_id=actor_user_id,
            reason=reason,
            expected_version=expected_version,
        )

    def patch_override(
        self,
        company_id: int,
        patch: Mapping[str, Any],
        *,
        actor_user_id: Optional[int],
        reason: Optional[str] = None,
        expected_version: Optional[int] = None,
    ) -> BookingPolicyAdminResponse:
        """
        Mescla o patch no override existente (semântica PATCH).

        Campos não enviados são preservados no documento persistido.

        Args:
            company_id: Tenant efetivo.
            patch: Patch parcial.
            actor_user_id: Usuário autenticado.
            reason: Motivo opcional de auditoria.

        Returns:
            Política efetiva após persistência.

        Raises:
            ValidationError: Payload inválido.
            ConflictError: Conflito de unicidade no banco.
            ValueError: ``company_id`` inválido.
        """
        return self._upsert_override(
            company_id,
            patch,
            merge_with_existing=True,
            actor_user_id=actor_user_id,
            reason=reason,
            expected_version=expected_version,
        )

    def deactivate_override(
        self,
        company_id: int,
        *,
        actor_user_id: Optional[int],
        reason: Optional[str] = None,
    ) -> BookingPolicyAdminResponse:
        """
        Desativa o override ativo (``is_active=False``) sem apagar defaults.

        Idempotente: se não há override ativo, retorna defaults sem nova auditoria.

        Args:
            company_id: Tenant efetivo.
            actor_user_id: Usuário autenticado.
            reason: Motivo opcional.

        Returns:
            Política efetiva (defaults).

        Raises:
            ValueError: ``company_id`` inválido.
        """
        self._require_company_id(company_id)
        row = self._get_active_row(company_id)
        if row is None:
            return self.get_policy(company_id)

        before = dict(row.policy_json) if isinstance(row.policy_json, dict) else {}
        row.is_active = False
        row.updated_by_user_id = actor_user_id
        row.updated_at = datetime.utcnow()
        record_policy_change(
            self.db,
            company_id=company_id,
            action="deactivate",
            before=before,
            after=None,
            actor_user_id=actor_user_id,
            reason=reason,
            commit=False,
        )
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return self.get_policy(company_id)

    def _upsert_override(
        self,
        company_id: int,
        document: Mapping[str, Any],
        *,
        merge_with_existing: bool,
        actor_user_id: Optional[int],
        reason: Optional[str],
        expected_version: Optional[int] = None,
    ) -> BookingPolicyAdminResponse:
        """
        Valida, persiste e audita create/update do override.

        Args:
            company_id: Tenant.
            document: Payload de política (sem ``reason``).
            merge_with_existing: True=PATCH, False=PUT.
            actor_user_id: Ator.
            reason: Motivo.
            expected_version: Se informado e houver override ativo, exige match.

        Returns:
            Resposta com política efetiva.

        Raises:
            ValidationError: Documento inválido.
            ConflictError: Violação de unicidade ou versão desatualizada.
        """
        self._require_company_id(company_id)
        if document is None or not isinstance(document, Mapping):
            raise ValidationError("Documento de política inválido")
        if "company_id" in document:
            raise ValidationError("company_id não é aceito no body")
        if not reason or not str(reason).strip():
            raise ValidationError("reason é obrigatório para alterar a política")

        incoming = deepcopy(dict(document))
        row = self._get_row_any(company_id)
        previous_override: Dict[str, Any] = {}
        if row is not None and isinstance(row.policy_json, dict):
            previous_override = dict(row.policy_json)

        if (
            expected_version is not None
            and row is not None
            and bool(row.is_active)
        ):
            current_version = int(row.version or 0)
            if current_version != int(expected_version):
                raise ConflictError(
                    "Versão da política desatualizada "
                    f"(esperado {expected_version}, atual {current_version})"
                )

        if merge_with_existing and row is not None and row.is_active:
            candidate_override = deep_merge(previous_override, incoming)
        else:
            # PUT: substitui; ou PATCH sem override ativo: documento enviado.
            candidate_override = incoming

        policy, error = merge_and_validate(candidate_override)
        if error or policy is None:
            raise ValidationError(
                f"Política de booking inválida: {error or 'validação falhou'}"
            )

        action = "create"
        before_snapshot: Optional[Dict[str, Any]] = None
        if row is None:
            row = BookingPolicyConfig(
                company_id=company_id,
                policy_json=candidate_override,
                version=1,
                is_active=True,
                updated_by_user_id=actor_user_id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            self.db.add(row)
        else:
            if row.is_active:
                action = "update"
                before_snapshot = previous_override
            else:
                action = "create"
                before_snapshot = None
            row.policy_json = candidate_override
            row.is_active = True
            row.version = int(row.version or 0) + 1
            row.updated_by_user_id = actor_user_id
            row.updated_at = datetime.utcnow()

        record_policy_change(
            self.db,
            company_id=company_id,
            action=action,
            before=before_snapshot,
            after=candidate_override,
            actor_user_id=actor_user_id,
            reason=reason,
            commit=False,
        )
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise ConflictError(
                "Conflito ao persistir política de booking do tenant"
            ) from exc
        except Exception:
            self.db.rollback()
            raise

        self.db.refresh(row)
        return self.get_policy(company_id)

    def _get_active_row(self, company_id: int) -> Optional[BookingPolicyConfig]:
        """
        Carrega override ativo do tenant.

        Args:
            company_id: Tenant.

        Returns:
            Linha ativa ou None.
        """
        return (
            self.db.query(BookingPolicyConfig)
            .filter(
                BookingPolicyConfig.company_id == company_id,
                BookingPolicyConfig.is_active.is_(True),
            )
            .first()
        )

    def _get_row_any(self, company_id: int) -> Optional[BookingPolicyConfig]:
        """
        Carrega a linha de override do tenant (ativa ou não).

        Args:
            company_id: Tenant.

        Returns:
            Linha ou None.
        """
        return (
            self.db.query(BookingPolicyConfig)
            .filter(BookingPolicyConfig.company_id == company_id)
            .first()
        )

    @staticmethod
    def _require_company_id(company_id: int) -> None:
        """
        Valida ``company_id`` positivo.

        Args:
            company_id: Valor a validar.

        Raises:
            ValueError: Se inválido.
        """
        if company_id is None or not isinstance(company_id, int) or company_id <= 0:
            raise ValueError("company_id é obrigatório para política de booking")
