"""
ResourceDomainService — regras de create/update/deactivate (R2-F3).
"""
from typing import TYPE_CHECKING, Optional

from app.modules.resource.domain.entities.resource import Resource
from app.modules.resource.domain.exceptions import UnknownResourceTypeError

if TYPE_CHECKING:
    from app.modules.resource.application.ports.resource_type_port import ResourceTypePort


class ResourceDomainService:
    """
    Serviço de domínio para operações de Resource.

    Args:
        type_port: Port de validação de resource_types do plugin.
    """

    def __init__(self, type_port: Optional["ResourceTypePort"] = None):
        self._type_port = type_port

    def create(
        self,
        company_id: int,
        location_id: int,
        name: str,
        slug: str,
        resource_type: str,
        capacity: int = 1,
        is_default: bool = False,
        plugin_id: str = "beauty",
    ) -> Resource:
        """
        Cria aggregate Resource após validar tipo no manifest.

        Args:
            company_id: Tenant.
            location_id: Unidade.
            name: Nome.
            slug: Slug.
            resource_type: Tipo canônico.
            capacity: Capacidade.
            is_default: Default do local.
            plugin_id: Plugin ativo (default beauty).

        Returns:
            Resource aggregate.

        Raises:
            UnknownResourceTypeError: Tipo não declarado.
        """
        if self._type_port is not None:
            resolved = self._type_port.resolve(plugin_id, resource_type)
            if resolved is None:
                raise UnknownResourceTypeError(
                    f"resource_type desconhecido: {resource_type}"
                )
            default_cap = resolved.get("default_capacity")
            if default_cap is not None and capacity < 1:
                capacity = int(default_cap)
        return Resource.create(
            company_id=company_id,
            location_id=location_id,
            name=name,
            slug=slug,
            resource_type=resource_type,
            capacity=capacity,
            is_default=is_default,
        )

    def update(
        self,
        resource: Resource,
        name: Optional[str] = None,
        capacity: Optional[int] = None,
    ) -> Resource:
        """
        Atualiza resource ativo.

        Args:
            resource: Aggregate carregado.
            name: Novo nome.
            capacity: Nova capacity.

        Returns:
            Aggregate mutado.
        """
        resource.update(name=name, capacity=capacity)
        return resource

    def deactivate(self, resource: Resource) -> Resource:
        """
        Desativa resource (soft).

        Args:
            resource: Aggregate.

        Returns:
            Aggregate mutado.
        """
        resource.deactivate()
        return resource
