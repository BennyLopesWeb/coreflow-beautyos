"""Testes CF-7 — core_waitlist + BeautyAgent + manifest expandido."""
from datetime import date

from app.models.fila import Fila, StatusFila
from app.modules.catalog.application.legacy_sync_service import LegacySyncService
from app.modules.customer.legacy_sync import CustomerLegacySyncService
from app.modules.waitlist.application.legacy_sync_service import WaitlistLegacySyncService
from app.modules.waitlist.domain.models import CoreWaitlist
from app.core.plugin.registry import plugin_registry


def test_waitlist_sync_from_legacy(
    db, cliente_exemplo, tranca_exemplo, service_image_exemplo, default_company
):
    """Sync cria core_waitlist a partir de Fila legado."""
    LegacySyncService(db).sync_all()
    CustomerLegacySyncService(db).sync_all()

    fila = Fila(
        company_id=default_company.id,
        cliente_id=cliente_exemplo.id,
        tranca_id=tranca_exemplo.id,
        service_image_id=service_image_exemplo.id,
        data=date.today(),
        posicao=1,
        status=StatusFila.WAITING,
        observacoes="Prefiro manhã",
    )
    db.add(fila)
    db.commit()
    db.refresh(fila)

    WaitlistLegacySyncService(db).sync_all()
    row = (
        db.query(CoreWaitlist)
        .filter(CoreWaitlist.legacy_fila_id == fila.id)
        .first()
    )
    assert row is not None
    assert row.legacy_cliente_id == cliente_exemplo.id
    assert row.position == 1
    assert row.notes == "Prefiro manhã"


def test_v1_waitlist_list(client, admin_headers, db, cliente_exemplo, tranca_exemplo, service_image_exemplo, default_company):
    """GET /v1/waitlist retorna itens sincronizados."""
    LegacySyncService(db).sync_all()
    CustomerLegacySyncService(db).sync_all()

    fila = Fila(
        company_id=default_company.id,
        cliente_id=cliente_exemplo.id,
        tranca_id=tranca_exemplo.id,
        service_image_id=service_image_exemplo.id,
        data=date.today(),
        posicao=2,
        status=StatusFila.WAITING,
    )
    db.add(fila)
    db.commit()

    response = client.get("/v1/waitlist", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["legacy_fila_id"] == fila.id


def test_v1_ai_analyze(client, admin_headers):
    """POST /v1/ai/analyze executa BeautyAgent protótipo."""
    response = client.post("/v1/ai/analyze", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["plugin_id"] == "beauty"
    assert "capabilities" in body
    assert "crm_followup" in body["capabilities"]
    assert body["pending_tasks"] >= 0


def test_plugin_manifest_expanded_fields():
    """Manifest beauty expõe campos SDK/AI expandidos (CF-7)."""
    manifest = plugin_registry.require("beauty")
    assert manifest.api_version == "1"
    assert manifest.has_ai_capability("crm_followup")
    assert "waitlist" in manifest.sdk.get("routes", {})
    assert "booking.created" in manifest.hooks
