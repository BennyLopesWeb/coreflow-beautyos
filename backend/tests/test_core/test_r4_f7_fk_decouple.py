"""
R4-F7 - Decouple fisico das FKs restantes para `agendamentos` - ADR-024 / RFC-003 M11.

Sucede test_r4_f6_payment_bridge.py (bridge Payment->booking_id + cutover
de disponibilidade). O gate R4-F6 documentou o bloqueio fisico do DROP de
`agendamentos`/`payments`/`schedules`: `Schedule` e `SatisfactionSurvey`
ainda tinham FK fisica para `agendamentos.id` (`NOT NULL` em `Schedule`),
e outras cinco tabelas (`payments`, `fila`, `queue_entries`, `financeiro`,
`notification_logs`) ainda referenciavam `agendamentos` por constraint
fisica mesmo com a coluna ja opcional.

R4-F7 remove essa ultima dependencia fisica:

- FK fisica para `agendamentos.id` removida de sete tabelas (`payments`,
  `schedules`, `satisfaction_surveys`, `fila`, `queue_entries`,
  `financeiro`, `notification_logs`) - `agendamento_id` permanece como
  `Integer` simples em todas, apenas para leitura historica.
- `schedules`/`satisfaction_surveys` ganham `booking_id` (FK nullable
  `core_bookings.id`, indexada) + `agendamento_id` nullable (mesmo padrao
  adotado em `payments` no R4-F6).
- `DisponibilidadeService._slots_ocupados` passa a ler ocupacao
  exclusivamente de `core_bookings` - a leitura de compatibilidade sobre
  `Agendamento` legado (mantida desde R4-F4/R4-F6) foi removida.

Prova que:

- APP_VERSION == 2.10.0-r4-f7.
- `Schedule` aceita `booking_id` preenchido com `agendamento_id=None`.
- `SatisfactionSurvey` aceita `booking_id` preenchido com
  `agendamento_id=None`.
- Nenhuma das sete tabelas tem mais FK fisica para `agendamentos` (via
  `sa.inspect(...).get_foreign_keys`).
- `DisponibilidadeService` continua marcando slot ocupado por
  `CoreBooking` com banco 100% sem `Agendamento` (core-only).
- A tabela `agendamentos` **nao foi removida** - CF6/CF9 continuam
  criando `Agendamento` diretamente via ORM sem erro.

O DROP fisico de `agendamentos`/`payments`/`schedules` continua fora de
escopo - explicitamente adiado para **R4-F8** (ver docs/sprints/R4-F7.md).

.. deprecated:: 2.11.0-r4-f8
    R4-F8 executou o DROP físico adiado acima — a tabela ``agendamentos``
    não existe mais e ``Agendamento`` deixou de ser um model SQLAlchemy
    mapeado (ver ``app/models/agendamento.py``). Os testes que
    dependiam de instanciar/consultar ``Agendamento`` via ORM (incluindo
    ``test_agendamentos_table_nao_foi_removida``, que documentava
    exatamente o oposto do que passou a ser verdade) foram removidos ou
    ajustados — ver ``test_r4_f8_drop_agendamentos.py`` para a cobertura
    completa do DROP. As garantias de FK física desta sprint (R4-F7)
    continuam válidas e cobertas abaixo.
"""
from datetime import date, datetime, timedelta
from decimal import Decimal

import sqlalchemy as sa

from app.core.config import settings
from app.models.agendamento import ReservationStatus
from app.models.financeiro import Financeiro, TipoMovimento
from app.models.fila import Fila, StatusFila
from app.models.notification_log import NotificationLog, NotificationStatus, NotificationType
from app.models.payment import Payment, PaymentStatus, PaymentType
from app.models.queue_entry import QueueEntry, QueueEntryStatus
from app.models.schedule import Schedule, ScheduleStatus
from app.models.satisfaction_survey import SatisfactionSurvey
from app.modules.booking.domain.models import CoreBooking
from app.modules.booking.domain.value_objects.booking_types import SyncStatus
from app.services.disponibilidade_service import DisponibilidadeService


_TABELAS_SEM_FK_FISICA = (
    "payments",
    "schedules",
    "satisfaction_surveys",
    "fila",
    "queue_entries",
    "financeiro",
    "notification_logs",
)


def _slot_for_day(db, catalog, offering, days_ahead: int) -> datetime:
    """
    Retorna primeiro horário disponível N dias à frente.

    Args:
        db: Sessão SQLAlchemy de teste.
        catalog: Fixture CoreCatalog sincronizado.
        offering: Fixture CoreOffering sincronizado.
        days_ahead: Deslocamento em dias para o slot candidato.

    Returns:
        datetime do primeiro horário disponível encontrado.
    """
    horarios = DisponibilidadeService(db).calcular_horarios_disponiveis(
        datetime.now() + timedelta(days=days_ahead),
        catalog.legacy_tranca_id,
        offering.legacy_service_image_id,
    )
    return next(h for h in horarios if h.disponivel).horario


def _criar_core_booking(db, default_company, cliente_exemplo, synced_catalog, days_ahead: int) -> CoreBooking:
    """
    Cria um ``CoreBooking`` pendente diretamente via ORM, sem ``Agendamento``.

    Args:
        db: Sessão SQLAlchemy de teste.
        default_company: Fixture de empresa.
        cliente_exemplo: Fixture de cliente legado.
        synced_catalog: Tupla (CoreCatalog, CoreOffering) sincronizados.
        days_ahead: Deslocamento em dias para o slot.

    Returns:
        CoreBooking persistido.
    """
    catalog, offering = synced_catalog
    slot = _slot_for_day(db, catalog, offering, days_ahead)
    booking = CoreBooking(
        company_id=default_company.id,
        customer_id=cliente_exemplo.id,
        catalog_id=catalog.id,
        offering_id=offering.id,
        scheduled_at=slot,
        status=ReservationStatus.PENDING_PAYMENT,
        price_total=Decimal("100.00"),
        deposit_pct=Decimal("0.30"),
        deposit_amount=Decimal("30.00"),
        remaining_amount=Decimal("70.00"),
        legacy_agendamento_id=None,
        sync_status=SyncStatus.SYNCED.value,
        version=1,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


def test_app_version_r4_f7():
    """APP_VERSION avançou de R4-F7 (pin exato relaxado em R4-F8+; ver test_app_version_r4_f8)."""
    assert settings.APP_VERSION.startswith("2.")


def test_nenhuma_tabela_tem_fk_fisica_para_agendamentos(db):
    """
    Nenhuma das sete tabelas afetadas mantém FK física para ``agendamentos``.

    Usa ``sa.inspect(...).get_foreign_keys`` sobre a engine de teste (schema
    criado via ``Base.metadata.create_all`` a partir dos models já
    atualizados nesta release) — equivalente ao que a migration
    ``cf015_r4_f7_decouple_fks`` garante em bancos reais.
    """
    inspector = sa.inspect(db.get_bind())
    for table_name in _TABELAS_SEM_FK_FISICA:
        fks = inspector.get_foreign_keys(table_name)
        referenciam_agendamentos = [
            fk for fk in fks if fk.get("referred_table") == "agendamentos"
        ]
        assert referenciam_agendamentos == [], (
            f"{table_name} ainda tem FK física para agendamentos: {referenciam_agendamentos}"
        )


def test_schedule_aceita_booking_id_sem_agendamento_id(db, default_company):
    """Schedule persiste com booking_id preenchido e agendamento_id=None (bridge R4-F7)."""
    sch = Schedule(
        company_id=default_company.id,
        agendamento_id=None,
        booking_id=123,
        data=date.today() + timedelta(days=90),
        inicio=datetime.now() + timedelta(days=90),
        fim=datetime.now() + timedelta(days=90, hours=1),
        status=ScheduleStatus.SCHEDULED,
    )
    db.add(sch)
    db.commit()
    db.refresh(sch)

    assert sch.id is not None
    assert sch.agendamento_id is None
    assert sch.booking_id == 123

    reloaded = db.query(Schedule).filter(Schedule.id == sch.id).first()
    assert reloaded.agendamento_id is None
    assert reloaded.booking_id == 123


def test_satisfaction_survey_aceita_booking_id_sem_agendamento_id(db, cliente_exemplo):
    """SatisfactionSurvey persiste com booking_id preenchido e agendamento_id=None (bridge R4-F7)."""
    survey = SatisfactionSurvey(
        agendamento_id=None,
        booking_id=456,
        cliente_id=cliente_exemplo.id,
        nota_geral=5,
    )
    db.add(survey)
    db.commit()
    db.refresh(survey)

    assert survey.id is not None
    assert survey.agendamento_id is None
    assert survey.booking_id == 456

    reloaded = db.query(SatisfactionSurvey).filter(SatisfactionSurvey.id == survey.id).first()
    assert reloaded.agendamento_id is None
    assert reloaded.booking_id == 456


def test_payment_fila_queue_entry_financeiro_notification_log_sem_fk_fisica(
    db, default_company, cliente_exemplo
):
    """
    Payment/Fila/QueueEntry/Financeiro/NotificationLog persistem com
    agendamento_id apontando para um id inexistente sem erro de integridade
    — confirma que a FK física foi removida (SQLite não teria bloqueado
    mesmo antes por padrão, mas a ausência de erro documenta o cenário —
    a garantia física em si é coberta por
    ``test_nenhuma_tabela_tem_fk_fisica_para_agendamentos``).
    """
    pag = Payment(agendamento_id=999999, tipo=PaymentType.DEPOSIT, valor=Decimal("10.00"))
    fila = Fila(
        company_id=default_company.id,
        cliente_id=cliente_exemplo.id,
        tranca_id=1,
        service_image_id=1,
        data=date.today() + timedelta(days=91),
        posicao=1,
        status=StatusFila.WAITING,
        agendamento_id=999999,
    )
    entry = QueueEntry(
        company_id=default_company.id,
        agendamento_id=999999,
        cliente_id=cliente_exemplo.id,
        posicao=1,
        data=date.today() + timedelta(days=91),
        status=QueueEntryStatus.WAITING,
    )
    fin = Financeiro(
        company_id=default_company.id,
        tipo=TipoMovimento.ENTRADA,
        descricao="Teste R4-F7",
        valor=Decimal("10.00"),
        agendamento_id=999999,
        data=datetime.now(),
    )
    log = NotificationLog(
        agendamento_id=999999,
        cliente_id=cliente_exemplo.id,
        tipo=NotificationType.WHATSAPP,
        status=NotificationStatus.PENDENTE,
        destinatario="11999999999",
    )
    db.add_all([pag, fila, entry, fin, log])
    db.commit()

    assert pag.id is not None and pag.agendamento_id == 999999
    assert fila.id is not None and fila.agendamento_id == 999999
    assert entry.id is not None and entry.agendamento_id == 999999
    assert fin.id is not None and fin.agendamento_id == 999999
    assert log.id is not None and log.agendamento_id == 999999


def test_disponibilidade_core_only_sem_leitura_de_agendamento(
    db, default_company, cliente_exemplo, synced_catalog
):
    """
    DisponibilidadeService continua marcando slot ocupado por CoreBooking
    com banco 100% sem Agendamento — confirma que o cutover core-only
    (iniciado no R4-F6) não depende de nenhuma leitura sobre
    ``agendamentos`` após a remoção da consulta legado em R4-F7 (tabela
    removida via DROP físico em R4-F8 — não há mais como consultá-la).
    """
    booking = _criar_core_booking(db, default_company, cliente_exemplo, synced_catalog, days_ahead=95)

    catalog, offering = synced_catalog
    horarios = DisponibilidadeService(db).calcular_horarios_disponiveis(
        booking.scheduled_at, catalog.legacy_tranca_id, offering.legacy_service_image_id
    )
    ocupado = next(h for h in horarios if h.horario == booking.scheduled_at)
    assert ocupado.disponivel is False
