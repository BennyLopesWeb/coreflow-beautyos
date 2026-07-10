"""
Exceções de domínio Booking (ADR-026 / ADR-031).
"""


class InvalidBookingStateTransitionError(Exception):
    """
    Transição de estado inválida no aggregate Booking (SM-1).

    Attributes:
        message: Código ou descrição do erro.
    """

    def __init__(self, message: str = "invalid_booking_state_transition") -> None:
        """
        Args:
            message: Detalhe da violação de state machine.
        """
        self.message = message
        super().__init__(message)


class OptimisticLockConflictError(Exception):
    """
    Conflito de optimistic lock — version esperada diverge (ADR-031).

    Attributes:
        message: Código do erro.
    """

    def __init__(self, message: str = "version_conflict") -> None:
        """
        Args:
            message: Detalhe do conflito de versão.
        """
        self.message = message
        super().__init__(message)
