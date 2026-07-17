"""
CatalogQueryAdapter — leitura catalog/offering via repository + legado (R2-F3b).
"""
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.tranca import Tranca
from app.modules.booking.domain.services.booking_domain_service import (
    OfferingSnapshot,
)
from app.modules.booking.domain.value_objects.booking_types import MoneySnapshot
from app.modules.catalog.infrastructure.repositories.catalog_repository import (
    SqlAlchemyCatalogRepository,
)
from app.services.service_image_service import ServiceImageService
from app.utils.service_image_precos import resolver_precos_imagem


class SqlAlchemyCatalogQueryAdapter:
    """
    Implementação read-only de ``CatalogQueryPort`` (booking cross-context).

    Usa ``CatalogRepository`` para metamodelo e serviços legado para preços
    (paridade Strangler). Satisfaz o Protocol definido em booking domain.

    Args:
        db: Sessão SQLAlchemy.
    """

    def __init__(self, db: Session):
        self._db = db
        self._repo = SqlAlchemyCatalogRepository(db)

    def get_offering_snapshot(
        self, catalog_id: int, offering_id: int, company_id: int
    ) -> OfferingSnapshot:
        """
        Monta snapshot com preços alinhados ao legado.

        Args:
            catalog_id: ID core catalog.
            offering_id: ID core offering.
            company_id: Tenant.

        Returns:
            OfferingSnapshot.

        Raises:
            ValueError: Mapeamento ou offering inválido.
        """
        catalog = self._repo.get_by_id(catalog_id, company_id)
        offering = self._repo.get_offering(offering_id, company_id)
        if not catalog or not catalog.legacy_tranca_id:
            raise ValueError(f"Catalog {catalog_id} sem mapeamento legado")
        if not offering or not offering.legacy_service_image_id:
            raise ValueError(f"Offering {offering_id} sem mapeamento legado")
        if offering.catalog_id != catalog.id:
            raise ValueError("Offering não pertence ao catalog informado")

        tranca = self._db.query(Tranca).filter(Tranca.id == catalog.legacy_tranca_id).first()
        catalog_active = bool(tranca and tranca.ativo)

        ServiceImageService(self._db).validar_imagem_da_tranca(
            catalog.legacy_tranca_id, offering.legacy_service_image_id
        )
        img = ServiceImageService(self._db).obter_imagem(offering.legacy_service_image_id)
        precos = resolver_precos_imagem(img)

        pct = Decimal(str(img.percentual_sinal or "0.30"))
        price_total = Decimal(str(precos["valor_total"]))
        deposit_amount = Decimal(str(precos["valor_sinal"]))
        remaining = Decimal(str(precos["valor_restante"]))
        duration = int(precos.get("duracao_minutos") or offering.duration_minutes or 30)

        return OfferingSnapshot(
            catalog_id=catalog.id,
            offering_id=offering.id,
            company_id=company_id,
            legacy_tranca_id=catalog.legacy_tranca_id,
            legacy_service_image_id=offering.legacy_service_image_id,
            duration_minutes=duration,
            catalog_active=catalog_active,
            pricing=MoneySnapshot(
                price_total=price_total,
                deposit_pct=pct,
                deposit_amount=deposit_amount,
                remaining_amount=remaining,
            ),
        )
