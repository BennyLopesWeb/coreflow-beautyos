"""
Políticas configuráveis de booking (FIX-CONFIG-01).

Tabela dedicada ``booking_policy_config``: ``CoreWorkflowConfig`` só armazena
``workflow_id`` + ``enabled`` (e permite ``company_id`` nulo), sem documento JSON
de política nem auditoria — inadequado para este caso.
"""
from app.modules.booking.domain.policy.activation import (
    calculate_minimum_activation_cents,
    cents_to_decimal,
    meets_minimum_activation,
    minimum_activation_from_price_total,
    money_to_cents,
)
from app.modules.booking.domain.policy.paid_amount import (
    EffectivePaidSnapshot,
    get_effective_paid_amount_cents,
    load_effective_paid_snapshots,
)
from app.modules.booking.domain.policy.audit import record_policy_change
from app.modules.booking.domain.policy.cancel_window import (
    can_cancel_approved,
    may_cancel_for_lifecycle,
)
from app.modules.booking.domain.policy.defaults import (
    get_installation_defaults,
    get_safe_fallback_policy,
)
from app.modules.booking.domain.policy.models import (
    BookingPolicyAudit,
    BookingPolicyConfig,
)
from app.modules.booking.domain.policy.resolver import BookingPolicyResolver
from app.modules.booking.domain.policy.schemas import BookingPolicy

__all__ = [
    "BookingPolicy",
    "BookingPolicyAudit",
    "BookingPolicyConfig",
    "BookingPolicyResolver",
    "EffectivePaidSnapshot",
    "calculate_minimum_activation_cents",
    "can_cancel_approved",
    "cents_to_decimal",
    "get_effective_paid_amount_cents",
    "get_installation_defaults",
    "get_safe_fallback_policy",
    "load_effective_paid_snapshots",
    "may_cancel_for_lifecycle",
    "meets_minimum_activation",
    "minimum_activation_from_price_total",
    "money_to_cents",
    "record_policy_change",
]
