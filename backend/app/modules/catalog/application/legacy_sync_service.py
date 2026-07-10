"""
Sincronização Strangler Fig — legado (Tranca/ServiceImage/Agendamento) → metamodelo CoreFlow.
"""
import re
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.models.tranca import Tranca
from app.models.service_image import ServiceImage
from app.models.agendamento import Agendamento
from app.modules.catalog.domain.models import CoreCatalog, CoreOffering
from app.modules.booking.domain.models import CoreBooking
from app.core.logging_config import get_logger

logger = get_logger("legacy_sync")


def _slugify(name: str, entity_id: int) -> str:
    """
    Gera slug URL-safe a partir do nome.

    Args:
        name: Nome da entidade.
        entity_id: ID para desambiguação.

    Returns:
        Slug normalizado.
    """
    base = re.sub(r"[^a-z0-9]+", "-", (name or "item").lower()).strip("-")
    return f"{base}-{entity_id}"[:120]


class LegacySyncService:
    """
    Sincroniza entidades legadas para tabelas genéricas do metamodelo CoreFlow.

    Idempotente — pode rodar no startup e após migrações.

    Args:
        db: Sessão SQLAlchemy.
    """

    def __init__(self, db: Session):
        self.db = db

    def sync_all(self) -> dict:
        """
        Executa sync completo catalog → offering → booking.

        Returns:
            Dict com contagens por entidade.
        """
        catalogs = self.sync_catalogs()
        offerings = self.sync_offerings()
        bookings = self.sync_bookings()
        return {"catalogs": catalogs, "offerings": offerings, "bookings": bookings}

    def sync_catalogs(self) -> int:
        """
        Sincroniza ``trancas`` → ``core_catalogs``.

        Returns:
            Quantidade processada.
        """
        trancas = self.db.query(Tranca).filter(Tranca.deleted_at.is_(None)).all()
        count = 0
        for t in trancas:
            existing = (
                self.db.query(CoreCatalog)
                .filter(CoreCatalog.legacy_tranca_id == t.id)
                .first()
            )
            slug = _slugify(t.nome, t.id)
            if existing:
                existing.name = t.nome
                existing.description = t.descricao
                existing.images = t.imagens or []
                existing.active = t.ativo
                existing.company_id = t.company_id or existing.company_id
            else:
                self.db.add(
                    CoreCatalog(
                        company_id=t.company_id or 1,
                        name=t.nome,
                        slug=slug,
                        description=t.descricao,
                        images=t.imagens or [],
                        active=t.ativo,
                        legacy_tranca_id=t.id,
                        plugin_metadata={"source": "beauty", "legacy": "Tranca"},
                    )
                )
            count += 1
        self.db.commit()
        logger.info(f"Sync catalogs: {count}")
        return count

    def sync_offerings(self) -> int:
        """
        Sincroniza ``service_images`` → ``core_offerings``.

        Returns:
            Quantidade processada.
        """
        images = (
            self.db.query(ServiceImage)
            .filter(ServiceImage.deleted_at.is_(None))
            .all()
        )
        count = 0
        for img in images:
            catalog = (
                self.db.query(CoreCatalog)
                .filter(CoreCatalog.legacy_tranca_id == img.service_id)
                .first()
            )
            if not catalog:
                self.sync_catalogs()
                catalog = (
                    self.db.query(CoreCatalog)
                    .filter(CoreCatalog.legacy_tranca_id == img.service_id)
                    .first()
                )
            if not catalog:
                continue

            existing = (
                self.db.query(CoreOffering)
                .filter(CoreOffering.legacy_service_image_id == img.id)
                .first()
            )
            company_id = catalog.company_id
            payload = dict(
                company_id=company_id,
                catalog_id=catalog.id,
                name=img.nome or f"Modelo {img.id}",
                description=img.descricao,
                price_total=img.valor_total,
                deposit_pct=img.percentual_sinal or Decimal("0.30"),
                deposit_amount=img.valor_sinal,
                duration_minutes=img.duracao_minutos,
                image_url=img.url,
                active=img.ativo,
                plugin_metadata={
                    "source": "beauty",
                    "legacy": "ServiceImage",
                    "complexity": img.nivel_complexidade,
                },
            )
            if existing:
                for key, val in payload.items():
                    setattr(existing, key, val)
            else:
                self.db.add(
                    CoreOffering(legacy_service_image_id=img.id, **payload)
                )
            count += 1
        self.db.commit()
        logger.info(f"Sync offerings: {count}")
        return count

    def sync_bookings(self) -> int:
        """
        Sincroniza ``agendamentos`` → ``core_bookings``.

        Returns:
            Quantidade processada.
        """
        agendamentos = (
            self.db.query(Agendamento)
            .filter(Agendamento.deleted_at.is_(None))
            .all()
        )
        count = 0
        for ag in agendamentos:
            catalog = (
                self.db.query(CoreCatalog)
                .filter(CoreCatalog.legacy_tranca_id == ag.tranca_id)
                .first()
            )
            offering = (
                self.db.query(CoreOffering)
                .filter(CoreOffering.legacy_service_image_id == ag.service_image_id)
                .first()
            )
            if not catalog or not offering:
                continue

            existing = (
                self.db.query(CoreBooking)
                .filter(CoreBooking.legacy_agendamento_id == ag.id)
                .first()
            )
            payload = dict(
                company_id=ag.company_id or catalog.company_id,
                customer_id=ag.cliente_id,
                catalog_id=catalog.id,
                offering_id=offering.id,
                scheduled_at=ag.data_hora,
                approved_at=ag.horario_aprovado,
                status=ag.status,
                payment_status=ag.status_pagamento,
                price_total=ag.valor_total,
                deposit_pct=ag.percentual_sinal,
                deposit_amount=ag.valor_sinal,
                remaining_amount=ag.valor_restante,
                deposit_paid=ag.sinal_pago,
                notes=ag.observacoes,
            )
            if existing:
                for key, val in payload.items():
                    setattr(existing, key, val)
            else:
                self.db.add(
                    CoreBooking(legacy_agendamento_id=ag.id, **payload)
                )
            count += 1
        self.db.commit()
        logger.info(f"Sync bookings: {count}")
        return count

    def resolve_legacy_ids(
        self, catalog_id: int, offering_id: int
    ) -> tuple[int, int]:
        """
        Resolve IDs genéricos para IDs legados (tranca, service_image).

        Args:
            catalog_id: ID core_catalogs.
            offering_id: ID core_offerings.

        Returns:
            Tupla (tranca_id, service_image_id).

        Raises:
            ValueError: Se mapeamento legado ausente.
        """
        catalog = self.db.query(CoreCatalog).filter(CoreCatalog.id == catalog_id).first()
        offering = (
            self.db.query(CoreOffering).filter(CoreOffering.id == offering_id).first()
        )
        if not catalog or not catalog.legacy_tranca_id:
            raise ValueError(f"Catalog {catalog_id} sem mapeamento legado")
        if not offering or not offering.legacy_service_image_id:
            raise ValueError(f"Offering {offering_id} sem mapeamento legado")
        if offering.catalog_id != catalog.id:
            raise ValueError("Offering não pertence ao catalog informado")
        return catalog.legacy_tranca_id, offering.legacy_service_image_id

    def sync_booking_from_agendamento(self, agendamento_id: int) -> Optional[CoreBooking]:
        """
        Sincroniza um agendamento recém-criado para core_bookings.

        Args:
            agendamento_id: ID do agendamento legado.

        Returns:
            CoreBooking ou None.
        """
        ag = self.db.query(Agendamento).filter(Agendamento.id == agendamento_id).first()
        if not ag:
            return None
        self.sync_bookings()
        return (
            self.db.query(CoreBooking)
            .filter(CoreBooking.legacy_agendamento_id == ag.id)
            .first()
        )
