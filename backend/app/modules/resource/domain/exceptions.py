"""
Exceções de domínio — Resource Engine (R2-F3).
"""


class InvalidResourceCapacityError(ValueError):
    """
    Capacidade inválida (deve ser >= 1).

    Raised when:
        create/update recebe capacity < 1.
    """


class ResourceInactiveError(ValueError):
    """
    Operação inválida sobre resource inativo.

    Raised when:
        allocate/update em resource deactivated.
    """


class UnknownResourceTypeError(ValueError):
    """
    Tipo de resource não declarado no plugin manifest.

    Raised when:
        ResourceTypePort.resolve falha para type_id.
    """
