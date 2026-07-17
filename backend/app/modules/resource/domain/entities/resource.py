"""
Aggregate Resource — domínio puro (ADR-007 / R2-F3).
"""
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from app.modules.resource.domain.exceptions import (
    InvalidResourceCapacityError,
    ResourceInactiveError,
)
from app.modules.resource.domain.value_objects.resource_types import (
    Capacity,
    ResourceTypeId,
)


@dataclass
class Resource:
    """
    Aggregate root Resource — recurso reservável genérico.

    Attributes:
        company_id: Tenant.
        location_id: Unidade física.
        name: Nome exibido.
        slug: Identificador URL-safe.
        resource_type: Tipo (chair, court, …).
        capacity: Vagas simultâneas.
        active: Disponível para alocação.
        is_default: Recurso padrão do local.
        plugin_metadata: Extensões do plugin.
        id: Persistido (None antes do save).
    """

    company_id: int
    location_id: int
    name: str
    slug: str
    resource_type: ResourceTypeId
    capacity: Capacity
    active: bool = True
    is_default: bool = False
    plugin_metadata: Dict[str, Any] = field(default_factory=dict)
    id: Optional[int] = None

    @classmethod
    def create(
        cls,
        company_id: int,
        location_id: int,
        name: str,
        slug: str,
        resource_type: str,
        capacity: int = 1,
        is_default: bool = False,
        plugin_metadata: Optional[Dict[str, Any]] = None,
    ) -> "Resource":
        """
        Factory para novo resource ativo.

        Args:
            company_id: Tenant.
            location_id: FK location.
            name: Nome.
            slug: Slug único por tenant.
            resource_type: Tipo canônico.
            capacity: Capacidade (>= 1).
            is_default: Se é default do local.
            plugin_metadata: Metadados opcionais.

        Returns:
            Resource pronto para persistência.

        Raises:
            InvalidResourceCapacityError: capacity < 1.
            ValueError: Campos obrigatórios ausentes.
        """
        if company_id < 1 or location_id < 1:
            raise ValueError("company_id e location_id são obrigatórios")
        if not (name or "").strip():
            raise ValueError("name é obrigatório")
        if not (slug or "").strip():
            raise ValueError("slug é obrigatório")
        return cls(
            company_id=company_id,
            location_id=location_id,
            name=name.strip(),
            slug=slug.strip().lower(),
            resource_type=ResourceTypeId(resource_type),
            capacity=Capacity(capacity),
            active=True,
            is_default=is_default,
            plugin_metadata=plugin_metadata or {},
        )

    def update(
        self,
        name: Optional[str] = None,
        capacity: Optional[int] = None,
        plugin_metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Atualiza campos mutáveis do resource.

        Args:
            name: Novo nome (opcional).
            capacity: Nova capacidade (opcional).
            plugin_metadata: Substitui metadata (opcional).

        Raises:
            ResourceInactiveError: Resource desativado.
            InvalidResourceCapacityError: capacity inválida.
        """
        if not self.active:
            raise ResourceInactiveError("resource inativo")
        if name is not None:
            if not name.strip():
                raise ValueError("name não pode ser vazio")
            self.name = name.strip()
        if capacity is not None:
            self.capacity = Capacity(capacity)
        if plugin_metadata is not None:
            self.plugin_metadata = plugin_metadata

    def deactivate(self) -> None:
        """
        Soft-deactivate (idempotente).

        Returns:
            None
        """
        self.active = False
        self.is_default = False
