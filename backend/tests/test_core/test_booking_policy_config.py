"""
FIX-CONFIG-01 — modelo, defaults, resolver, validação e auditoria de políticas.
"""
from __future__ import annotations

from datetime import datetime

import pytest
from pydantic import ValidationError

from app.models.company import Company, CompanyPlan, CompanySegment
from app.modules.booking.domain.policy.audit import record_policy_change
from app.modules.booking.domain.policy.defaults import get_installation_defaults
from app.modules.booking.domain.policy.models import (
    BookingPolicyAudit,
    BookingPolicyConfig,
)
from app.modules.booking.domain.policy.resolver import BookingPolicyResolver
from app.modules.booking.domain.policy.schemas import (
    BookingPolicy,
    CancellationPolicy,
    ExpirationPolicy,
    ReversalPolicy,
)
from app.modules.booking.domain.policy.validation import merge_and_validate


def _create_company(db, slug: str, nome: str) -> Company:
    """
    Cria empresa auxiliar para testes de política.

    Args:
        db: Sessão SQLAlchemy.
        slug: Slug único.
        nome: Nome comercial.

    Returns:
        Company persistida.
    """
    company = Company(
        nome=nome,
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


def _upsert_override(db, company_id: int, policy_json: dict, *, active: bool = True) -> BookingPolicyConfig:
    """
    Insere ou atualiza override de política para um tenant.

    Args:
        db: Sessão.
        company_id: Tenant.
        policy_json: Documento de override.
        active: Se o override está ativo.

    Returns:
        Linha ``BookingPolicyConfig`` persistida.
    """
    now = datetime.utcnow()
    row = (
        db.query(BookingPolicyConfig)
        .filter(BookingPolicyConfig.company_id == company_id)
        .first()
    )
    if row is None:
        row = BookingPolicyConfig(
            company_id=company_id,
            policy_json=policy_json,
            version=1,
            is_active=active,
            created_at=now,
            updated_at=now,
        )
        db.add(row)
    else:
        row.policy_json = policy_json
        row.is_active = active
        row.version = int(row.version or 1) + 1
        row.updated_at = now
    db.commit()
    db.refresh(row)
    return row


# ---------------------------------------------------------------------------
# Defaults (1–8)
# ---------------------------------------------------------------------------


def test_01_sem_override_retorna_defaults(db, default_company):
    """Sem override, o resolver devolve defaults da instalação."""
    policy = BookingPolicyResolver(db).resolve(default_company.id)
    assert policy == get_installation_defaults()


def test_02_after_hours_default_2(db, default_company):
    """``after_hours`` default é 2."""
    policy = BookingPolicyResolver(db).resolve(default_company.id)
    assert policy.expiration.after_hours == 2


def test_03_reversao_cancelado_desabilitada(db, default_company):
    """Reversão de cancelado vem desabilitada."""
    policy = BookingPolicyResolver(db).resolve(default_company.id)
    assert policy.reversal_cancelled.enabled is False


def test_04_reversao_expirado_desabilitada(db, default_company):
    """Reversão de expirado vem desabilitada."""
    policy = BookingPolicyResolver(db).resolve(default_company.id)
    assert policy.reversal_expired.enabled is False


def test_05_modo_reversao_new_booking_only(db, default_company):
    """Modo padrão de reversão é ``new_booking_only``."""
    policy = BookingPolicyResolver(db).resolve(default_company.id)
    assert policy.reversal_cancelled.mode == "new_booking_only"
    assert policy.reversal_expired.mode == "new_booking_only"


def test_06_block_financial_reopen_habilitado(db, default_company):
    """``block_financial_reopen`` vem habilitado."""
    policy = BookingPolicyResolver(db).resolve(default_company.id)
    assert policy.manual_status.block_financial_reopen is True


def test_07_cancelamento_cliente_desabilitado(db, default_company):
    """Cancelamento de cliente vem desabilitado."""
    policy = BookingPolicyResolver(db).resolve(default_company.id)
    assert policy.cancellation.client_allowed is False


def test_08_defaults_imutaveis():
    """Defaults são objetos frozen previsíveis."""
    policy = get_installation_defaults()
    with pytest.raises(ValidationError):
        policy.expiration.after_hours = 99  # type: ignore[misc]
    with pytest.raises(AttributeError):
        policy.cancellation.allowed_roles.append("customer")  # type: ignore[attr-defined]
    assert policy.expiration.after_hours == 2


# ---------------------------------------------------------------------------
# Override por tenant (9–14)
# ---------------------------------------------------------------------------


def test_09_10_11_14_empresas_isoladas(db):
    """Empresa A e B recebem configs distintas; A não recebe a de B."""
    co_a = _create_company(db, "cfg01-a", "Empresa A")
    co_b = _create_company(db, "cfg01-b", "Empresa B")
    _upsert_override(db, co_a.id, {"expiration": {"after_hours": 6}})
    _upsert_override(db, co_b.id, {"expiration": {"after_hours": 12}})

    resolver = BookingPolicyResolver(db)
    pol_a = resolver.resolve(co_a.id)
    pol_b = resolver.resolve(co_b.id)

    assert pol_a.expiration.after_hours == 6
    assert pol_b.expiration.after_hours == 12
    assert pol_a.expiration.after_hours != pol_b.expiration.after_hours
    # Defaults da instalação intactos
    assert get_installation_defaults().expiration.after_hours == 2


def test_12_ausencia_override_usa_defaults(db):
    """Ausência de override usa defaults."""
    co = _create_company(db, "cfg01-no-ov", "Sem Override")
    policy = BookingPolicyResolver(db).resolve(co.id)
    assert policy.expiration.after_hours == 2
    assert policy.cancellation.approved_min_hours_before == 24


def test_13_override_parcial_completa_defaults(db):
    """Override parcial completa campos ausentes com defaults."""
    co = _create_company(db, "cfg01-partial", "Partial")
    _upsert_override(db, co.id, {"expiration": {"after_hours": 4}})
    policy = BookingPolicyResolver(db).resolve(co.id)
    assert policy.expiration.after_hours == 4
    assert policy.expiration.reference == "created_at"
    assert policy.cancellation.approved_min_hours_before == 24
    assert policy.reversal_cancelled.enabled is False


# ---------------------------------------------------------------------------
# Validação (15–23)
# ---------------------------------------------------------------------------


def test_15_after_hours_menor_que_1_rejeitado():
    """``after_hours < 1`` é rejeitado."""
    with pytest.raises(ValidationError):
        ExpirationPolicy(after_hours=0)


def test_16_after_hours_maior_que_168_rejeitado():
    """``after_hours > 168`` é rejeitado."""
    with pytest.raises(ValidationError):
        ExpirationPolicy(after_hours=169)


def test_17_janela_cancelamento_fora_range():
    """Janela de cancelamento fora de ``0..720`` é rejeitada."""
    with pytest.raises(ValidationError):
        CancellationPolicy(approved_min_hours_before=-1)
    with pytest.raises(ValidationError):
        CancellationPolicy(approved_min_hours_before=721)


def test_18_role_desconhecida_rejeitada():
    """Role desconhecida é rejeitada."""
    with pytest.raises(ValidationError):
        CancellationPolicy(allowed_roles=["superuser"])


def test_19_status_desconhecido_rejeitado():
    """Status desconhecido é rejeitado."""
    with pytest.raises(ValidationError):
        CancellationPolicy(allowed_from_statuses=["pending", "fantasma"])


def test_20_lista_estados_invalidos_rejeitada():
    """Lista de estados elegíveis inválida é rejeitada."""
    with pytest.raises(ValidationError):
        ExpirationPolicy(eligible_statuses=[])
    with pytest.raises(ValidationError):
        ExpirationPolicy(eligible_statuses=["nao_existe"])


def test_21_restore_original_rejeitado():
    """``restore_original`` é rejeitado neste MVP."""
    with pytest.raises(ValidationError):
        ReversalPolicy(mode="restore_original")
    policy, err = merge_and_validate(
        {"reversal_cancelled": {"mode": "restore_original"}}
    )
    assert policy is None
    assert err is not None


def test_22_config_invalida_nao_falha_aberto(db, caplog):
    """Configuração inválida não falha aberto — retorna fallback seguro."""
    import logging

    co = _create_company(db, "cfg01-bad", "Bad Config")
    _upsert_override(db, co.id, {"expiration": {"after_hours": 0}})
    resolver_logger = "app.modules.booking.domain.policy.resolver"
    with caplog.at_level(logging.WARNING, logger=resolver_logger):
        policy = BookingPolicyResolver(db).resolve(co.id)
    assert policy.expiration.after_hours == 2
    assert policy == get_installation_defaults()
    # Usa getMessage(): record.message só existe após Formatter.format.
    assert any(
        "booking_policy_invalid_override" in r.getMessage()
        for r in caplog.records
    ), caplog.messages


def test_23_chave_desconhecida_nao_altera_silenciosamente(db, caplog):
    """Payload com chave desconhecida não altera silenciosamente a política."""
    co = _create_company(db, "cfg01-extra", "Extra Keys")
    _upsert_override(
        db,
        co.id,
        {"expiration": {"after_hours": 8, "hack_flag": True}},
    )
    policy = BookingPolicyResolver(db).resolve(co.id)
    assert policy.expiration.after_hours == 2  # fallback, não 8
    assert not hasattr(policy.expiration, "hack_flag")


def test_protecao_financeira_cancelamento():
    """Não aceita remoção total de proteção financeira no cancelamento."""
    with pytest.raises(ValidationError):
        CancellationPolicy(set_payment_cancelled=False, soft_delete=False)


# ---------------------------------------------------------------------------
# Isolamento (24–27)
# ---------------------------------------------------------------------------


def test_24_25_busca_sempre_por_company_id(db):
    """Busca sempre usa ``company_id``; A não resolve override de B."""
    co_a = _create_company(db, "cfg01-iso-a", "Iso A")
    co_b = _create_company(db, "cfg01-iso-b", "Iso B")
    _upsert_override(db, co_b.id, {"cancellation": {"approved_min_hours_before": 48}})

    pol_a = BookingPolicyResolver(db).resolve(co_a.id)
    pol_b = BookingPolicyResolver(db).resolve(co_b.id)

    assert pol_a.cancellation.approved_min_hours_before == 24
    assert pol_b.cancellation.approved_min_hours_before == 48


def test_26_ausencia_tenant_nao_produz_global(db):
    """Ausência de tenant não produz configuração global implícita."""
    with pytest.raises(ValueError, match="company_id"):
        BookingPolicyResolver(db).resolve(None)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="company_id"):
        BookingPolicyResolver(db).resolve_optional(None)


def test_27_company_id_invalido_nao_infere_tenant(db):
    """``company_id`` inválido não infere tenant nem usa fallback permissivo."""
    with pytest.raises(ValueError):
        BookingPolicyResolver(db).resolve(0)
    with pytest.raises(ValueError):
        BookingPolicyResolver(db).resolve(-1)
    # company inexistente sem override → defaults (não erro aberto)
    policy = BookingPolicyResolver(db).resolve(999_999)
    assert policy == get_installation_defaults()


# ---------------------------------------------------------------------------
# Auditoria (28–31)
# ---------------------------------------------------------------------------


def test_28_29_30_estrutura_auditoria(db):
    """Auditoria preserva tenant e snapshots distinguíveis sem secrets/bookings."""
    co = _create_company(db, "cfg01-audit", "Audit Co")
    before = {"expiration": {"after_hours": 2}}
    after = {"expiration": {"after_hours": 6}}
    row = record_policy_change(
        db,
        company_id=co.id,
        action="update",
        before=before,
        after=after,
        actor_user_id=None,
        reason="teste",
        commit=True,
    )
    assert row.company_id == co.id
    assert row.before_json != row.after_json
    assert row.before_json["expiration"]["after_hours"] == 2
    assert row.after_json["expiration"]["after_hours"] == 6
    dumped = str(row.before_json) + str(row.after_json) + str(row.reason)
    assert "password" not in dumped.lower()
    assert "booking_id" not in dumped
    assert "payment_status" not in dumped


def test_31_leitura_resolver_nao_cria_audit(db):
    """Leitura do resolver não cria falso evento de alteração."""
    co = _create_company(db, "cfg01-read", "Read Only")
    before = db.query(BookingPolicyAudit).count()
    BookingPolicyResolver(db).resolve(co.id)
    after = db.query(BookingPolicyAudit).count()
    assert after == before


def test_override_inativo_usa_defaults(db):
    """Override inativo é ignorado (defaults da instalação)."""
    co = _create_company(db, "cfg01-inactive", "Inactive")
    _upsert_override(
        db,
        co.id,
        {"expiration": {"after_hours": 10}},
        active=False,
    )
    policy = BookingPolicyResolver(db).resolve(co.id)
    assert policy.expiration.after_hours == 2


def test_booking_policy_model_dump_roundtrip():
    """Documento canônico serializa e revalida sem perda."""
    policy = get_installation_defaults()
    again = BookingPolicy.model_validate(policy.to_public_dict())
    assert again == policy
