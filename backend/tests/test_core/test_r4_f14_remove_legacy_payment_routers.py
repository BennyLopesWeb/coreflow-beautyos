"""R4-F14 — Remoção dos routers legado pagamentos/payments.

Cobertura:
- APP_VERSION == 2.17.0-r4-f14.
- Módulos ``app.routers.pagamentos`` e ``app.routers.payments`` ausentes.
- LegacyGone ainda responde 410 em /pagamentos* e /payments*.
"""
import importlib

import pytest

from app.core.config import settings
from app.core.legacy_gone import match_legacy_gone


def test_app_version_r4_f14():
    """APP_VERSION avançou de R4-F14 (pin exato relaxado em R4-F15+)."""
    assert settings.APP_VERSION.startswith("2.")


def test_routers_legado_removidos():
    """Módulos pagamentos/payments não existem mais."""
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("app.routers.pagamentos")
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("app.routers.payments")


def test_legacy_gone_cobre_prefixos_completos():
    """Prefixos /pagamentos e /payments cobrem o surface antigo."""
    assert match_legacy_gone("/pagamentos").successor == "/v1/payments"
    assert match_legacy_gone("/pagamentos/sinal").successor == "/v1/payments"
    assert match_legacy_gone("/pagamentos/comprovante/1").successor == "/v1/payments"
    assert match_legacy_gone("/payments").successor == "/v1/payments"
    assert match_legacy_gone("/payments/deposit").successor == "/v1/payments"
    assert match_legacy_gone("/payments/reservation/1").successor == "/v1/payments"
    assert match_legacy_gone("/v1/payments") is None


def test_http_410_sem_routers(client):
    """HTTP 410 persiste via middleware sem handlers registrados."""
    assert client.post("/pagamentos/sinal", json={"agendamento_id": 1}).status_code == 410
    assert client.post("/payments/deposit", json={"agendamento_id": 1}).status_code == 410
    assert client.get("/payments/reservation/1").status_code == 410
