"""
Políticas configuráveis de booking (FIX-CONFIG-01).

Tabela dedicada ``booking_policy_config``: ``CoreWorkflowConfig`` só armazena
``workflow_id`` + ``enabled`` (e permite ``company_id`` nulo), sem documento JSON
de política nem auditoria — inadequado para este caso.
"""
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
    "can_cancel_approved",
    "get_installation_defaults",
    "get_safe_fallback_policy",
    "may_cancel_for_lifecycle",
    "record_policy_change",
]
