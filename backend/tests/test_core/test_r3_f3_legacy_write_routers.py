"""R3-F3 — Remoção de writes legado + QueueEntry → CreateBookingHandler."""
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.exceptions import ValidationError
from app.models.queue_entry import QueueEntry, QueueEntryStatus
from app.modules.booking.domain.models import CoreBooking
from app.services.disponibilidade_service import DisponibilidadeService
from app.services.queue_entry_service import QueueEntryService


def test_app_version_r3_f3():
    """Versão da release R3-F3."""
    assert settings.APP_VERSION == "2.3.0-r3-f3"


def test_agenda_write_methods_removed(client: TestClient):
    """POST/PUT/DELETE /agenda/agendamentos → 405 Method Not Allowed."""
    assert client.post("/agenda/agendamentos", json={}).status_code == 405
    assert client.put("/agenda/agendamentos/1", json={}).status_code == 405
    assert client.delete("/agenda/agendamentos/1").status_code == 405


def test_reservations_write_methods_removed(client: TestClient):
    """POST/PUT/DELETE /reservations removidos (405 no resource; 404 em subpaths)."""
    assert client.post("/reservations", json={}).status_code == 405
    # Subpaths removidos não têm rota → 404; DELETE no recurso → 405
    assert client.put("/reservations/1/approve").status_code in (404, 405)
    assert client.put("/reservations/1/reject", json={"motivo": "x"}).status_code in (404, 405)
    assert client.put("/reservations/1/complete").status_code in (404, 405)
    assert client.delete("/reservations/1").status_code == 405


def test_agenda_disponibilidade_still_works(
    client: TestClient, tranca_exemplo, service_image_exemplo
):
    """GET /agenda/disponibilidade permanece disponível."""
    data_hora = datetime.now() + timedelta(days=1)
    data_hora = data_hora.replace(hour=10, minute=0, second=0, microsecond=0)
    response = client.get(
        "/agenda/disponibilidade",
        params={
            "data": data_hora.isoformat(),
            "tranca_id": tranca_exemplo.id,
            "service_image_id": service_image_exemplo.id,
        },
    )
    assert response.status_code == 200
    assert "horarios" in response.json()


def test_aprovar_com_horario_cria_booking_core(
    db, synced_catalog, cliente_exemplo
):
    """
    QueueEntryService.aprovar_com_horario usa CreateBookingHandler (R3-F3).

    Args:
        db: Sessão de teste.
        synced_catalog: Fixture catalog/offering sincronizados.
        cliente_exemplo: Cliente legado.
    """
    catalog, offering = synced_catalog
    horarios = DisponibilidadeService(db).calcular_horarios_disponiveis(
        datetime.now() + timedelta(days=3),
        catalog.legacy_tranca_id,
        offering.legacy_service_image_id,
    )
    slot = next(h for h in horarios if h.disponivel)

    entry = QueueEntry(
        company_id=1,
        cliente_id=cliente_exemplo.id,
        tranca_id=catalog.legacy_tranca_id,
        service_image_id=offering.legacy_service_image_id,
        posicao=1,
        data=slot.horario.date(),
        horario_entrada=datetime.now().time(),
        status=QueueEntryStatus.WAITING,
        observacoes="fila r3-f3",
        mesmo_dia=0,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    updated = QueueEntryService(db).aprovar_com_horario(entry.id, slot.horario)
    assert updated.agendamento_id is not None
    assert updated.status == QueueEntryStatus.WAITING

    booking = (
        db.query(CoreBooking)
        .filter(CoreBooking.legacy_agendamento_id == updated.agendamento_id)
        .first()
    )
    assert booking is not None
    assert booking.customer_id == cliente_exemplo.id
    assert booking.catalog_id == catalog.id


def test_aprovar_com_horario_sem_catalog_raise(
    db, cliente_exemplo, tranca_exemplo, service_image_exemplo
):
    """Sem sync catalog/offering → ValidationError."""
    entry = QueueEntry(
        company_id=1,
        cliente_id=cliente_exemplo.id,
        tranca_id=tranca_exemplo.id,
        service_image_id=service_image_exemplo.id,
        posicao=1,
        data=datetime.now().date(),
        horario_entrada=datetime.now().time(),
        status=QueueEntryStatus.WAITING,
        mesmo_dia=0,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    with pytest.raises(ValidationError):
        QueueEntryService(db).aprovar_com_horario(
            entry.id, datetime.now() + timedelta(days=2)
        )
