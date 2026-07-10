"""
Eventos de domínio do bounded context Identity.
"""
from app.shared.events.domain_event import DomainEvent

USER_REGISTERED = "identity.user.registered"
COMPANY_CREATED = "identity.company.created"


def user_registered(
    company_id: int,
    user_id: int,
    email: str,
    role: str,
) -> DomainEvent:
    """
    Factory para evento de registro de usuário.

    Args:
        company_id: Tenant padrão associado.
        user_id: ID do usuário criado.
        email: E-mail do usuário.
        role: Papel RBAC inicial.

    Returns:
        DomainEvent publicável.
    """
    return DomainEvent(
        event_type=USER_REGISTERED,
        company_id=company_id,
        aggregate_id=str(user_id),
        aggregate_type="User",
        payload={"user_id": user_id, "email": email, "role": role},
    )


def company_created(company_id: int, slug: str, nome: str) -> DomainEvent:
    """
    Factory para evento de criação de empresa.

    Args:
        company_id: ID da empresa.
        slug: Slug público.
        nome: Nome comercial.

    Returns:
        DomainEvent publicável.
    """
    return DomainEvent(
        event_type=COMPANY_CREATED,
        company_id=company_id,
        aggregate_id=str(company_id),
        aggregate_type="Company",
        payload={"slug": slug, "nome": nome},
    )
