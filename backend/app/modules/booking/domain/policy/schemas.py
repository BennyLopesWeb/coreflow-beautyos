"""
Schemas tipados e imutáveis das políticas de booking (FIX-CONFIG-01).
"""
from __future__ import annotations

from typing import Dict, Literal, Mapping, Sequence, Tuple

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.user_company import CompanyRole
from app.modules.booking.domain.value_objects.booking_types import BookingLifecycleStatus


ExpirationReference = Literal["created_at", "scheduled_at"]
ReversalMode = Literal["new_booking_only"]
ResultStatus = Literal["expired"]

# Roles aceitos na política (RBAC + alias ``admin`` = papéis administrativos).
POLICY_ROLE_VALUES = frozenset(
    {r.value for r in CompanyRole} | {"admin"}
)

# Status lifecycle canônicos (domínio).
LIFECYCLE_STATUS_VALUES = frozenset(s.value for s in BookingLifecycleStatus)

# Status ORM elegíveis à expiração automática (caminho atual).
EXPIRATION_ELIGIBLE_STATUS_VALUES = frozenset(
    {
        "pending_payment",
        "pending_approval",
        "waiting_time_confirmation",
        "pendente",
        "pending",
    }
)


def default_manual_transitions() -> Dict[str, Tuple[str, ...]]:
    """
    Matriz fechada espelhando a FSM do aggregate ``Booking``.

    Returns:
        Mapa ``from_status → tuple(to_status, ...)`` (lifecycle canônico).
    """
    return {
        BookingLifecycleStatus.PENDING.value: (
            BookingLifecycleStatus.APPROVED.value,
            BookingLifecycleStatus.REJECTED.value,
            BookingLifecycleStatus.CANCELLED.value,
            BookingLifecycleStatus.EXPIRED.value,
        ),
        BookingLifecycleStatus.APPROVED.value: (
            BookingLifecycleStatus.CANCELLED.value,
            BookingLifecycleStatus.RESCHEDULED.value,
            BookingLifecycleStatus.COMPLETED.value,
            BookingLifecycleStatus.NO_SHOW.value,
        ),
        BookingLifecycleStatus.REJECTED.value: (),
        BookingLifecycleStatus.CANCELLED.value: (),
        BookingLifecycleStatus.RESCHEDULED.value: (),
        BookingLifecycleStatus.COMPLETED.value: (),
        BookingLifecycleStatus.NO_SHOW.value: (),
        BookingLifecycleStatus.EXPIRED.value: (),
    }


class ExpirationPolicy(BaseModel):
    """
    Políticas de expiração automática de bookings pendentes.

    Attributes:
        enabled: Se a expiração automática está ativa.
        after_hours: Horas após o timestamp de referência.
        reference: Campo de referência temporal.
        eligible_statuses: Status ORM/lifecycle elegíveis.
        require_unpaid_deposit: Exige ``deposit_paid=False``.
        result_status: Status resultante (somente ``expired``).
        touch_payment_status: Se altera ``payment_status`` na expiração.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    enabled: bool = True
    after_hours: int = Field(default=2, ge=1, le=168)
    reference: ExpirationReference = "created_at"
    eligible_statuses: Tuple[str, ...] = ("pending_payment",)
    require_unpaid_deposit: bool = True
    result_status: ResultStatus = "expired"
    touch_payment_status: bool = False

    @field_validator("eligible_statuses", mode="before")
    @classmethod
    def _validate_eligible(cls, value: Sequence[str]) -> Tuple[str, ...]:
        """
        Valida lista fechada de status elegíveis à expiração.

        Args:
            value: Lista/tupla de status.

        Returns:
            Tupla normalizada (imutável).

        Raises:
            ValueError: Lista vazia ou status desconhecido.
        """
        if not value:
            raise ValueError("eligible_statuses não pode ser vazia")
        items = list(value)
        unknown = [s for s in items if s not in EXPIRATION_ELIGIBLE_STATUS_VALUES]
        if unknown:
            raise ValueError(f"status elegíveis desconhecidos: {unknown}")
        return tuple(items)


class CancellationPolicy(BaseModel):
    """
    Políticas de cancelamento manual.

    Attributes:
        enabled: Cancelamento habilitado.
        allowed_roles: Roles autorizados (RBAC + ``admin``).
        client_allowed: Cliente final pode cancelar.
        approved_min_hours_before: Antecedência mínima (approved).
        allowed_from_statuses: Lifecycle de origem.
        set_payment_cancelled: Alinha ``payment_status=cancelled``.
        soft_delete: Aplica soft-delete.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    enabled: bool = True
    allowed_roles: Tuple[str, ...] = ("owner", "admin")
    client_allowed: bool = False
    approved_min_hours_before: int = Field(default=24, ge=0, le=720)
    allowed_from_statuses: Tuple[str, ...] = ("pending", "approved")
    set_payment_cancelled: bool = True
    soft_delete: bool = True

    @field_validator("allowed_roles", mode="before")
    @classmethod
    def _validate_roles(cls, value: Sequence[str]) -> Tuple[str, ...]:
        """
        Valida roles contra o conjunto RBAC + alias admin.

        Args:
            value: Roles.

        Returns:
            Tupla normalizada.

        Raises:
            ValueError: Role desconhecida.
        """
        items = list(value or [])
        unknown = [r for r in items if r not in POLICY_ROLE_VALUES]
        if unknown:
            raise ValueError(f"roles desconhecidas: {unknown}")
        return tuple(items)

    @field_validator("allowed_from_statuses", mode="before")
    @classmethod
    def _validate_from_statuses(cls, value: Sequence[str]) -> Tuple[str, ...]:
        """
        Valida status de origem canônicos do lifecycle.

        Args:
            value: Status.

        Returns:
            Tupla normalizada.

        Raises:
            ValueError: Status inválido ou lista vazia.
        """
        if not value:
            raise ValueError("allowed_from_statuses não pode ser vazia")
        items = list(value)
        unknown = [s for s in items if s not in LIFECYCLE_STATUS_VALUES]
        if unknown:
            raise ValueError(f"status de origem desconhecidos: {unknown}")
        return tuple(items)

    @model_validator(mode="after")
    def _protect_financial_flags(self) -> "CancellationPolicy":
        """
        Impede configuração que remova toda proteção financeira.

        Returns:
            Self.

        Raises:
            ValueError: Ambos soft_delete e set_payment_cancelled falsos.
        """
        if not self.set_payment_cancelled and not self.soft_delete:
            raise ValueError(
                "cancelamento não pode desabilitar soft_delete e "
                "set_payment_cancelled simultaneamente"
            )
        return self


class ReversalPolicy(BaseModel):
    """
    Política de reversão (cancelado ou expirado).

    Attributes:
        enabled: Reversão habilitada.
        allowed_roles: Roles autorizados.
        mode: Somente ``new_booking_only`` no MVP.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    enabled: bool = False
    allowed_roles: Tuple[str, ...] = ()
    mode: ReversalMode = "new_booking_only"

    @field_validator("allowed_roles", mode="before")
    @classmethod
    def _validate_roles(cls, value: Sequence[str] | None) -> Tuple[str, ...]:
        """
        Valida roles de reversão.

        Args:
            value: Roles.

        Returns:
            Tupla normalizada.

        Raises:
            ValueError: Role desconhecida.
        """
        items = list(value or [])
        unknown = [r for r in items if r not in POLICY_ROLE_VALUES]
        if unknown:
            raise ValueError(f"roles desconhecidas: {unknown}")
        return tuple(items)

    @field_validator("mode", mode="before")
    @classmethod
    def _reject_restore_original(cls, value: str) -> str:
        """
        Rejeita ``restore_original`` neste MVP.

        Args:
            value: Modo.

        Returns:
            Modo validado.

        Raises:
            ValueError: Se modo for restore_original ou desconhecido.
        """
        if value == "restore_original":
            raise ValueError(
                "restore_original não é permitido neste MVP; use new_booking_only"
            )
        if value != "new_booking_only":
            raise ValueError(f"modo de reversão inválido: {value}")
        return value


class ManualStatusPolicy(BaseModel):
    """
    Preparação para alteração manual de status (consumida no FIX-02b-write).

    Attributes:
        enabled: Alteração manual habilitada.
        allowed_transitions: Matriz fechada lifecycle.
        block_financial_reopen: Impede reabrir confirmação financeira.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    enabled: bool = True
    allowed_transitions: Mapping[str, Tuple[str, ...]] = Field(
        default_factory=default_manual_transitions
    )
    block_financial_reopen: bool = True

    @field_validator("allowed_transitions", mode="before")
    @classmethod
    def _validate_transitions(
        cls, value: Mapping[str, Sequence[str]]
    ) -> Dict[str, Tuple[str, ...]]:
        """
        Valida chaves/valores da matriz contra lifecycle canônico.

        Args:
            value: Matriz.

        Returns:
            Cópia normalizada com tuplas imutáveis.

        Raises:
            ValueError: Status desconhecido.
        """
        normalized: Dict[str, Tuple[str, ...]] = {}
        for src, targets in value.items():
            if src not in LIFECYCLE_STATUS_VALUES:
                raise ValueError(f"status de origem desconhecido: {src}")
            target_list = list(targets)
            bad = [t for t in target_list if t not in LIFECYCLE_STATUS_VALUES]
            if bad:
                raise ValueError(f"status de destino desconhecidos: {bad}")
            normalized[src] = tuple(target_list)
        return normalized


ActivationMode = Literal["percentage_with_cap", "tiered_percentage"]


class ActivationPolicy(BaseModel):
    """
    Política de entrada mínima para ativação (CONFIG-DEPOSIT-POLICY-01).

    Attributes:
        mode: ``percentage_with_cap`` ou ``tiered_percentage``.
        currency: Moeda ISO (somente BRL na v1).
        percentage: Percentual do modo com teto (0–100).
        cap_cents: Teto em centavos (obrigatório em percentage_with_cap).
        standard_percentage: Percentual abaixo do limiar (tiered).
        high_value_threshold_cents: Limiar de alto valor em centavos.
        high_value_percentage: Percentual a partir do limiar (>= standard).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    mode: ActivationMode = "percentage_with_cap"
    currency: Literal["BRL"] = "BRL"
    percentage: int | None = None
    cap_cents: int | None = None
    standard_percentage: int | None = None
    high_value_threshold_cents: int | None = None
    high_value_percentage: int | None = None

    @model_validator(mode="after")
    def _validate_mode_contract(self) -> "ActivationPolicy":
        """
        Valida campos obrigatórios por modo.

        Returns:
            Instância validada.

        Raises:
            ValueError: Contrato do modo violado.
        """
        if self.currency != "BRL":
            raise ValueError("currency deve ser BRL nesta versão")

        if self.mode == "percentage_with_cap":
            if self.percentage is None or self.cap_cents is None:
                raise ValueError(
                    "percentage_with_cap exige percentage e cap_cents"
                )
            if not (0 <= int(self.percentage) <= 100):
                raise ValueError("percentage deve estar entre 0 e 100")
            if int(self.cap_cents) < 0:
                raise ValueError("cap_cents não pode ser negativo")
            if any(
                v is not None
                for v in (
                    self.standard_percentage,
                    self.high_value_threshold_cents,
                    self.high_value_percentage,
                )
            ):
                raise ValueError(
                    "campos de faixa não são permitidos em percentage_with_cap"
                )
            return self

        if self.mode == "tiered_percentage":
            if (
                self.standard_percentage is None
                or self.high_value_threshold_cents is None
                or self.high_value_percentage is None
            ):
                raise ValueError(
                    "tiered_percentage exige standard_percentage, "
                    "high_value_threshold_cents e high_value_percentage"
                )
            if not (0 <= int(self.standard_percentage) <= 100):
                raise ValueError("standard_percentage deve estar entre 0 e 100")
            if not (0 <= int(self.high_value_percentage) <= 100):
                raise ValueError(
                    "high_value_percentage deve estar entre 0 e 100"
                )
            if int(self.high_value_threshold_cents) <= 0:
                raise ValueError("high_value_threshold_cents deve ser > 0")
            if int(self.high_value_percentage) < int(self.standard_percentage):
                raise ValueError(
                    "high_value_percentage deve ser >= standard_percentage"
                )
            if self.cap_cents is not None and int(self.cap_cents) < 0:
                raise ValueError("cap_cents não pode ser negativo")
            if self.percentage is not None:
                raise ValueError(
                    "percentage não é permitido em tiered_percentage"
                )
            return self

        raise ValueError(f"mode de ativação inválido: {self.mode}")


def default_activation_policy() -> ActivationPolicy:
    """
    Default de instalação: 20% com teto de R$ 100,00.

    Returns:
        ``ActivationPolicy`` legado equivalente.
    """
    return ActivationPolicy(
        mode="percentage_with_cap",
        currency="BRL",
        percentage=20,
        cap_cents=10_000,
    )


class BookingPolicy(BaseModel):
    """
    Documento canônico imutável de políticas de booking.

    Attributes:
        expiration: Grupo expiração.
        cancellation: Grupo cancelamento.
        reversal_cancelled: Reversão de cancelado.
        reversal_expired: Reversão de expirado.
        manual_status: Alteração manual de status.
        activation: Entrada mínima para ativação.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    expiration: ExpirationPolicy = Field(default_factory=ExpirationPolicy)
    cancellation: CancellationPolicy = Field(default_factory=CancellationPolicy)
    reversal_cancelled: ReversalPolicy = Field(default_factory=ReversalPolicy)
    reversal_expired: ReversalPolicy = Field(default_factory=ReversalPolicy)
    manual_status: ManualStatusPolicy = Field(default_factory=ManualStatusPolicy)
    activation: ActivationPolicy = Field(default_factory=default_activation_policy)

    def to_public_dict(self) -> dict:
        """
        Serializa a política para persistência/auditoria (sem secrets).

        Returns:
            Dict JSON-serializável.
        """
        return self.model_dump()
