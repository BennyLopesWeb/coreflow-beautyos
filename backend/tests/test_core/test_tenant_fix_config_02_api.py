"""
FIX-CONFIG-02 — API administrativa tenant-scoped de política de booking.
"""
from __future__ import annotations

from datetime import datetime

import pytest

from app.core.security import create_access_token, get_password_hash
from app.models.company import Company, CompanyPlan, CompanySegment
from app.models.user import User
from app.models.user_company import CompanyRole
from app.modules.booking.domain.policy.models import (
    BookingPolicyAudit,
    BookingPolicyConfig,
)
from app.modules.booking.domain.policy.resolver import BookingPolicyResolver
from app.services.company_service import CompanyService


def _create_company(db, slug: str, nome: str | None = None) -> Company:
    """
    Cria empresa auxiliar para testes FIX-CONFIG-02.

    Args:
        db: Sessão.
        slug: Slug único.
        nome: Nome comercial.

    Returns:
        Company persistida.
    """
    company = Company(
        nome=nome or slug,
        slug=slug,
        segmento=CompanySegment.TRANCISTA,
        plano=CompanyPlan.FREE,
        timezone="America/Sao_Paulo",
        ativo=True,
    )
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


def _create_user(
    db,
    email: str,
    *,
    company: Company | None = None,
    role: CompanyRole = CompanyRole.OWNER,
    is_superuser: bool = False,
) -> User:
    """
    Cria usuário com membership opcional.

    Args:
        db: Sessão.
        email: E-mail único.
        company: Tenant.
        role: Papel RBAC.
        is_superuser: Flag superusuário.

    Returns:
        User persistido.
    """
    user = User(
        email=email,
        nome="Config02 User",
        hashed_password=get_password_hash("123456"),
        ativo=True,
        is_superuser=is_superuser,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    if company is not None:
        CompanyService(db).assign_user(user, company, role)
    return user


def _auth_headers(user: User, company: Company | None = None, role: str = "owner") -> dict:
    """
    Monta Authorization Bearer.

    Args:
        user: Usuário.
        company: Tenant no JWT.
        role: Role string no JWT.

    Returns:
        Headers HTTP.
    """
    data = {"sub": str(user.id), "email": user.email}
    if company is not None:
        data["company_id"] = company.id
        data["role"] = role
    return {"Authorization": f"Bearer {create_access_token(data=data)}"}


def _count_audits(db, company_id: int) -> int:
    """
    Conta eventos de auditoria do tenant.

    Args:
        db: Sessão.
        company_id: Tenant.

    Returns:
        Quantidade de linhas.
    """
    return (
        db.query(BookingPolicyAudit)
        .filter(BookingPolicyAudit.company_id == company_id)
        .count()
    )


# ---------------------------------------------------------------------------
# Autenticação
# ---------------------------------------------------------------------------


def test_01_get_sem_bearer_401(client):
    """GET sem Bearer → 401."""
    resp = client.get("/admin/booking-policy")
    assert resp.status_code == 401, resp.text


def test_02_put_sem_bearer_401(client):
    """PUT sem Bearer → 401."""
    resp = client.put(
        "/admin/booking-policy",
        json={"cancellation": {"approved_min_hours_before": 48}},
    )
    assert resp.status_code == 401, resp.text


def test_03_usuario_nao_admin_403(client, db, default_company):
    """Usuário customer (não admin) → 403."""
    user = _create_user(
        db,
        "cfg02-customer@test.local",
        company=default_company,
        role=CompanyRole.CUSTOMER,
    )
    resp = client.get(
        "/admin/booking-policy",
        headers=_auth_headers(user, default_company, role="customer"),
    )
    assert resp.status_code == 403, resp.text


def test_04_admin_sem_tenant_403(client, db):
    """Admin sem tenant efetivo → 403."""
    user = _create_user(db, "cfg02-orphan@test.local", company=None)
    resp = client.get("/admin/booking-policy", headers=_auth_headers(user))
    assert resp.status_code == 403, resp.text


def test_05_superuser_sem_tenant_403(client, db):
    """Superuser sem tenant efetivo → 403."""
    user = _create_user(
        db, "cfg02-su@test.local", company=None, is_superuser=True
    )
    resp = client.get("/admin/booking-policy", headers=_auth_headers(user))
    assert resp.status_code == 403, resp.text


# ---------------------------------------------------------------------------
# Isolamento
# ---------------------------------------------------------------------------


def test_06_09_tenant_a_isola_de_b(client, db, default_company):
    """Tenant A lê/altera só A; B permanece intacto."""
    company_b = _create_company(db, "cfg02-co-b")
    admin_a = _create_user(db, "cfg02-a@test.local", company=default_company)
    admin_b = _create_user(db, "cfg02-b@test.local", company=company_b)

    resp_b = client.put(
        "/admin/booking-policy",
        json={"cancellation": {"approved_min_hours_before": 72}},
        headers=_auth_headers(admin_b, company_b),
    )
    assert resp_b.status_code == 200, resp_b.text

    resp_a_get = client.get(
        "/admin/booking-policy",
        headers=_auth_headers(admin_a, default_company),
    )
    assert resp_a_get.status_code == 200, resp_a_get.text
    body_a = resp_a_get.json()
    assert body_a["company_id"] == default_company.id
    assert body_a["policy"]["cancellation"]["approved_min_hours_before"] == 24
    assert body_a["has_active_override"] is False

    resp_a_put = client.put(
        "/admin/booking-policy",
        json={"cancellation": {"approved_min_hours_before": 36}},
        headers=_auth_headers(admin_a, default_company),
    )
    assert resp_a_put.status_code == 200, resp_a_put.text
    assert (
        resp_a_put.json()["policy"]["cancellation"]["approved_min_hours_before"] == 36
    )

    resp_b_after = client.get(
        "/admin/booking-policy",
        headers=_auth_headers(admin_b, company_b),
    )
    assert resp_b_after.json()["policy"]["cancellation"]["approved_min_hours_before"] == 72


def test_10_company_id_no_body_rejeitado(client, db, default_company):
    """company_id no body é rejeitado (422 extra forbid)."""
    admin = _create_user(db, "cfg02-cid@test.local", company=default_company)
    resp = client.put(
        "/admin/booking-policy",
        json={
            "company_id": 999,
            "cancellation": {"approved_min_hours_before": 48},
        },
        headers=_auth_headers(admin, default_company),
    )
    assert resp.status_code == 422, resp.text


def test_11_12_sem_tenant_e_config_b_nao_vaza(client, db, default_company):
    """Ausência de tenant não usa fallback; config inválida de B não aparece em A."""
    company_b = _create_company(db, "cfg02-bad-b")
    now = datetime.utcnow()
    db.add(
        BookingPolicyConfig(
            company_id=company_b.id,
            policy_json={"expiration": {"after_hours": 0}},
            version=1,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
    )
    db.commit()

    orphan = _create_user(db, "cfg02-no-tenant@test.local", company=None)
    resp = client.get("/admin/booking-policy", headers=_auth_headers(orphan))
    assert resp.status_code == 403, resp.text

    admin_a = _create_user(db, "cfg02-safe-a@test.local", company=default_company)
    resp_a = client.get(
        "/admin/booking-policy",
        headers=_auth_headers(admin_a, default_company),
    )
    assert resp_a.status_code == 200
    assert resp_a.json()["policy"]["expiration"]["after_hours"] == 2


# ---------------------------------------------------------------------------
# Leitura e defaults
# ---------------------------------------------------------------------------


def test_13_15_get_sem_override_defaults(client, db, default_company):
    """GET sem override retorna defaults; source=default."""
    admin = _create_user(db, "cfg02-def@test.local", company=default_company)
    audits_before = _count_audits(db, default_company.id)
    resp = client.get(
        "/admin/booking-policy",
        headers=_auth_headers(admin, default_company),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["source"] == "default"
    assert body["has_active_override"] is False
    assert body["override"] is None
    assert body["policy"]["cancellation"]["approved_min_hours_before"] == 24
    assert body["policy"]["expiration"]["after_hours"] == 2
    assert _count_audits(db, default_company.id) == audits_before


def test_14_16_17_get_com_override_sem_side_effect(client, db, default_company):
    """GET com override retorna efetivos; não cria auditoria nem altera banco."""
    admin = _create_user(db, "cfg02-getov@test.local", company=default_company)
    put = client.put(
        "/admin/booking-policy",
        json={"cancellation": {"approved_min_hours_before": 48}},
        headers=_auth_headers(admin, default_company),
    )
    assert put.status_code == 200
    audits_after_put = _count_audits(db, default_company.id)
    version = put.json()["version"]

    resp = client.get(
        "/admin/booking-policy",
        headers=_auth_headers(admin, default_company),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["source"] == "override"
    assert body["has_active_override"] is True
    assert body["policy"]["cancellation"]["approved_min_hours_before"] == 48
    assert body["override"]["cancellation"]["approved_min_hours_before"] == 48
    assert body["version"] == version
    assert _count_audits(db, default_company.id) == audits_after_put


# ---------------------------------------------------------------------------
# Escrita
# ---------------------------------------------------------------------------


def test_18_21_patch_parcial_preserva_e_reflete(
    client, db, default_company
):
    """PATCH parcial preserva campos; GET posterior reflete merge."""
    admin = _create_user(db, "cfg02-patch@test.local", company=default_company)
    headers = _auth_headers(admin, default_company)

    r1 = client.put(
        "/admin/booking-policy",
        json={
            "cancellation": {"approved_min_hours_before": 48},
            "expiration": {"after_hours": 6},
        },
        headers=headers,
    )
    assert r1.status_code == 200, r1.text

    r2 = client.patch(
        "/admin/booking-policy",
        json={"cancellation": {"approved_min_hours_before": 36}},
        headers=headers,
    )
    assert r2.status_code == 200, r2.text
    policy = r2.json()["policy"]
    assert policy["cancellation"]["approved_min_hours_before"] == 36
    assert policy["expiration"]["after_hours"] == 6  # preservado

    r3 = client.get("/admin/booking-policy", headers=headers)
    assert r3.json()["policy"]["expiration"]["after_hours"] == 6


def test_19_20_put_substitui_override(client, db, default_company):
    """PUT substitui o documento de override (campos omitidos saem do override)."""
    admin = _create_user(db, "cfg02-put@test.local", company=default_company)
    headers = _auth_headers(admin, default_company)

    client.put(
        "/admin/booking-policy",
        json={
            "cancellation": {"approved_min_hours_before": 48},
            "expiration": {"after_hours": 8},
        },
        headers=headers,
    )
    r2 = client.put(
        "/admin/booking-policy",
        json={"cancellation": {"approved_min_hours_before": 30}},
        headers=headers,
    )
    assert r2.status_code == 200, r2.text
    override = r2.json()["override"]
    assert override == {"cancellation": {"approved_min_hours_before": 30}}
    # expiration volta ao default na política efetiva
    assert r2.json()["policy"]["expiration"]["after_hours"] == 2


def test_22_26_27_payload_invalido_nao_persiste_nem_audita(
    client, db, default_company
):
    """Valores inválidos → 400; banco e auditoria intactos."""
    admin = _create_user(db, "cfg02-bad@test.local", company=default_company)
    headers = _auth_headers(admin, default_company)
    audits_before = _count_audits(db, default_company.id)

    resp = client.put(
        "/admin/booking-policy",
        json={"expiration": {"after_hours": 0}},
        headers=headers,
    )
    assert resp.status_code == 400, resp.text
    assert _count_audits(db, default_company.id) == audits_before
    assert (
        db.query(BookingPolicyConfig)
        .filter(BookingPolicyConfig.company_id == default_company.id)
        .first()
        is None
    )


def test_24_25_tipo_e_chave_desconhecida(client, db, default_company):
    """Tipos inválidos e chaves desconhecidas são rejeitados."""
    admin = _create_user(db, "cfg02-types@test.local", company=default_company)
    headers = _auth_headers(admin, default_company)

    r_type = client.patch(
        "/admin/booking-policy",
        json={"cancellation": {"approved_min_hours_before": "vinte"}},
        headers=headers,
    )
    assert r_type.status_code == 400, r_type.text

    r_extra = client.patch(
        "/admin/booking-policy",
        json={"expiration": {"after_hours": 6, "hack_flag": True}},
        headers=headers,
    )
    assert r_extra.status_code == 400, r_extra.text

    r_top = client.put(
        "/admin/booking-policy",
        json={"unknown_group": {"x": 1}},
        headers=headers,
    )
    assert r_top.status_code == 422, r_top.text


def test_28_29_alteracao_valida_cria_auditoria_tenant_scoped(
    client, db, default_company
):
    """Alteração válida cria auditoria apenas do tenant."""
    company_b = _create_company(db, "cfg02-aud-b")
    admin_a = _create_user(db, "cfg02-aud-a@test.local", company=default_company)
    before_a = _count_audits(db, default_company.id)
    before_b = _count_audits(db, company_b.id)

    resp = client.put(
        "/admin/booking-policy",
        json={
            "cancellation": {"approved_min_hours_before": 40},
            "reason": "ajuste operacional",
        },
        headers=_auth_headers(admin_a, default_company),
    )
    assert resp.status_code == 200, resp.text
    assert _count_audits(db, default_company.id) == before_a + 1
    assert _count_audits(db, company_b.id) == before_b

    row = (
        db.query(BookingPolicyAudit)
        .filter(BookingPolicyAudit.company_id == default_company.id)
        .order_by(BookingPolicyAudit.id.desc())
        .first()
    )
    assert row is not None
    assert row.action == "create"
    assert row.actor_user_id == admin_a.id
    assert row.reason == "ajuste operacional"


# ---------------------------------------------------------------------------
# Desativação
# ---------------------------------------------------------------------------


def test_30_32_delete_volta_defaults_e_isola(client, db, default_company):
    """DELETE desativa override; A volta a defaults; B intacto."""
    company_b = _create_company(db, "cfg02-del-b")
    admin_a = _create_user(db, "cfg02-del-a@test.local", company=default_company)
    admin_b = _create_user(db, "cfg02-del-b@test.local", company=company_b)

    client.put(
        "/admin/booking-policy",
        json={"cancellation": {"approved_min_hours_before": 60}},
        headers=_auth_headers(admin_b, company_b),
    )
    client.put(
        "/admin/booking-policy",
        json={"cancellation": {"approved_min_hours_before": 50}},
        headers=_auth_headers(admin_a, default_company),
    )
    audits_before = _count_audits(db, default_company.id)

    resp = client.delete(
        "/admin/booking-policy",
        headers=_auth_headers(admin_a, default_company),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["source"] == "default"
    assert body["has_active_override"] is False
    assert body["policy"]["cancellation"]["approved_min_hours_before"] == 24
    assert _count_audits(db, default_company.id) == audits_before + 1

    resp_b = client.get(
        "/admin/booking-policy",
        headers=_auth_headers(admin_b, company_b),
    )
    assert resp_b.json()["policy"]["cancellation"]["approved_min_hours_before"] == 60


# ---------------------------------------------------------------------------
# Regressão
# ---------------------------------------------------------------------------


def test_33_resolver_continua(db, default_company):
    """Resolver permanece funcional após API (sem side-effect neste teste)."""
    policy = BookingPolicyResolver(db).resolve(default_company.id)
    assert policy.cancellation.approved_min_hours_before == 24


def test_34_override_via_api_consumido_pelo_resolver(client, db, default_company):
    """Override criado pela API é visto pelo BookingPolicyResolver."""
    admin = _create_user(db, "cfg02-res@test.local", company=default_company)
    client.put(
        "/admin/booking-policy",
        json={"cancellation": {"approved_min_hours_before": 55}},
        headers=_auth_headers(admin, default_company),
    )
    policy = BookingPolicyResolver(db).resolve(default_company.id)
    assert policy.cancellation.approved_min_hours_before == 55
