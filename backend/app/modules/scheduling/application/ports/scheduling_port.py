"""
SchedulingPort — contrato hexagonal para disponibilidade (ADR-029 estágio 1).

Commands e domain consomem esta interface; adapters ACL encapsulam legado.
"""
from datetime import datetime
from typing import Optional, Protocol


class SchedulingPort(Protocol):
    """
    Port para verificação de disponibilidade de slots.

    Estágio 1 (R2-F0.5): adapter ACL mapeia resource_id → legado internamente.
    Estágio 2 (R2-F3): adapter consome ResourcePort / core_resources.
    """

    def check_availability(
        self,
        company_id: int,
        resource_id: int,
        starts_at: datetime,
        ends_at: datetime,
        worker_id: Optional[int] = None,
        offering_id: Optional[int] = None,
        legacy_tranca_id: Optional[int] = None,
        legacy_service_image_id: Optional[int] = None,
    ) -> bool:
        """
        Verifica se o slot está disponível para reserva.

        Args:
            company_id: Tenant.
            resource_id: ID core resource (ou catalog mapeado via ACL até F3).
            starts_at: Início do slot.
            ends_at: Fim do slot.
            worker_id: Worker opcional.
            offering_id: Offering core para duração (opcional).

        Returns:
            True se disponível; False se conflito ou indisponível.
        """
        ...
