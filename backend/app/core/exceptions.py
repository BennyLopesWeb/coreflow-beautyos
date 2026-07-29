"""
Exceções customizadas da aplicação
Centraliza tratamento de erros
"""
from fastapi import HTTPException, status


class TrancaProException(HTTPException):
    """Exceção base da aplicação"""
    pass


class NotFoundError(TrancaProException):
    """Recurso não encontrado"""
    def __init__(self, resource: str, identifier: str = None):
        detail = f"{resource} não encontrado"
        if identifier:
            detail += f": {identifier}"
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail
        )


class ValidationError(TrancaProException):
    """Erro de validação"""
    def __init__(self, message: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )


class BusinessRuleError(TrancaProException):
    """Erro de regra de negócio"""
    def __init__(self, message: str):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=message
        )


class ConflictError(TrancaProException):
    """Conflito de dados (ex: telefone duplicado)"""
    def __init__(self, message: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=message
        )


class IdempotencyKeyRequiredError(ValidationError):
    """Header Idempotency-Key ausente em POST mutating (ADR-031)."""

    def __init__(self) -> None:
        super().__init__("idempotency_key_required")


class IdempotencyKeyReusedError(ConflictError):
    """Mesma Idempotency-Key com body diferente (ADR-031)."""

    def __init__(self) -> None:
        super().__init__("idempotency_key_reused")


class VersionConflictError(ConflictError):
    """Optimistic lock — version divergente (ADR-031)."""

    def __init__(self) -> None:
        super().__init__("version_conflict")


class DepositRequiredError(ConflictError):
    """Approve bloqueado — sinal não confirmado (ADR-028)."""

    def __init__(self) -> None:
        super().__init__("deposit_required")


class MinimumDepositNotMetError(ValidationError):
    """
    Ativação bloqueada — valor de entrada abaixo do mínimo
    (FIX-BOOKING-MIN-DEPOSIT-QUOTE-01).
    """

    def __init__(
        self,
        minimum_activation_cents: int,
        *,
        currency: str = "BRL",
    ) -> None:
        """
        Monta erro 400 com mínimo exigido em centavos.

        Args:
            minimum_activation_cents: Mínimo recalculado no servidor.
            currency: Moeda ISO (padrão BRL).
        """
        from decimal import Decimal

        reais = (Decimal(minimum_activation_cents) / Decimal(100)).quantize(
            Decimal("0.01")
        )
        message = (
            f"O valor mínimo de entrada para este serviço é R$ {reais}."
        )
        # detail estruturado (compatível com clientes que leem string ou dict)
        HTTPException.__init__(
            self,
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "MINIMUM_DEPOSIT_NOT_MET",
                "message": message,
                "minimum_activation_cents": minimum_activation_cents,
                "currency": currency,
            },
        )


class CancelPolicyViolationError(ConflictError):
    """Cancel bloqueado — policy 24h (ADR-026 amendment / R2-F2b)."""

    def __init__(self) -> None:
        super().__init__("cancel_policy_violation")

