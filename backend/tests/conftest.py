"""
Configuração compartilhada para testes
Fixtures e setup comum
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.db.base import Base
from app.db.session import get_db
from app.models import *  # Importa todos os models
from app.modules.catalog.domain.models import CoreCatalog, CoreOffering  # noqa: F401
from app.modules.booking.domain.models import CoreBooking  # noqa: F401
from app.modules.scheduling.domain.models import (  # noqa: F401
    CoreLocation,
    CoreResource,
    CoreScheduleBlock,
    CoreWorker,
)
from app.modules.customer.domain.models import CoreCustomer  # noqa: F401
from app.shared.events.outbox import CoreEventOutbox  # noqa: F401
from app.shared.events.kafka_dlq import CoreEventDlq  # noqa: F401
from app.modules.payments.domain.models import CorePayment  # noqa: F401
from app.modules.waitlist.domain.models import CoreWaitlist  # noqa: F401
from app.modules.workflow.domain.models import CoreWorkflowRun  # noqa: F401
from app.modules.workflow.domain.config_models import CoreWorkflowConfig  # noqa: F401
from app.modules.order.domain.models import CoreOrder  # noqa: F401
from app.modules.invoice.domain.models import CoreInvoice  # noqa: F401
from app.models.inventory_item import InventoryItem  # noqa: F401
from app.modules.asset.domain.models import CoreAsset  # noqa: F401
from app.modules.inventory.domain.models import CoreInventory  # noqa: F401
from app.modules.push.domain.models import CoreDeviceToken  # noqa: F401
from app.modules.mobile.domain.models import CoreCanaryPromotion  # noqa: F401
from app.shared.idempotency.models import IdempotencyKey  # noqa: F401


# Database de teste (SQLite em memória)
TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def _load_plugins():
    """
    Carrega plugins CoreFlow em todos os testes.

    Returns:
        None
    """
    from app.core.plugin.registry import plugin_registry
    plugin_registry.load_all()


@pytest.fixture(autouse=True)
def _bootstrap_default_company(db):
    """
    Garante empresa demo em todos os testes (multi-tenant Fase A).

    Args:
        db: Sessão de teste.
    """
    from app.services.company_service import CompanyService
    CompanyService(db).ensure_default_company()


@pytest.fixture(scope="function")
def db():
    """
    Fixture para sessão de banco de dados de teste
    Cria banco em memória para cada teste
    """
    # Cria todas as tabelas
    Base.metadata.create_all(bind=engine)
    
    # Cria sessão
    session = TestingSessionLocal()
    
    try:
        yield session
    finally:
        session.close()
        # Limpa tabelas
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    """
    Fixture para cliente de teste HTTP
    Usa FastAPI TestClient
    """
    from fastapi.testclient import TestClient
    from app.main import app
    
    # Override dependency para usar banco de teste
    def override_get_db():
        try:
            yield db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def booking_headers():
    """
    Headers obrigatórios para POST /v1/bookings (R2-F1b Idempotency-Key).

    Returns:
        Callable ``(key=None, correlation_id=None) -> dict`` de headers HTTP.
    """
    import uuid

    def _make(key=None, correlation_id=None):
        headers = {"Idempotency-Key": key or str(uuid.uuid4())}
        if correlation_id:
            headers["X-Correlation-Id"] = correlation_id
        return headers

    return _make


@pytest.fixture
def default_company(db):
    """
    Empresa demo para isolamento multi-tenant nos testes.

    Args:
        db: Sessão de teste.

    Returns:
        Company padrão.
    """
    from app.services.company_service import CompanyService
    return CompanyService(db).ensure_default_company()


@pytest.fixture
def admin_user(db, default_company):
    """
    Fixture para usuário administrador de teste.

    Args:
        db: Sessão SQLAlchemy de teste.
        default_company: Tenant demo.

    Returns:
        User: Usuário com is_superuser=True e role owner.
    """
    from app.models.user import User
    from app.models.user_company import CompanyRole
    from app.services.company_service import CompanyService
    from app.core.security import get_password_hash

    user = User(
        email="admin@test.com",
        nome="Admin Teste",
        hashed_password=get_password_hash("123456"),
        ativo=True,
        is_superuser=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    CompanyService(db).assign_user(user, default_company, CompanyRole.OWNER)
    return user


@pytest.fixture
def admin_headers(admin_user, default_company):
    """
    Cabeçalhos HTTP com token JWT de administrador.

    Args:
        admin_user: Usuário admin criado pela fixture homônima.
        default_company: Tenant demo.

    Returns:
        dict: Headers com Authorization Bearer para TestClient.
    """
    from app.core.security import create_access_token

    token = create_access_token(
        data={
            "sub": str(admin_user.id),
            "email": admin_user.email,
            "company_id": default_company.id,
            "role": "owner",
        }
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def cliente_exemplo(db, default_company):
    """
    Fixture para criar cliente de exemplo
    """
    from app.models.cliente import Cliente
    cliente = Cliente(
        nome="Maria Silva",
        telefone="11999999999",
        email="maria@email.com",
        company_id=default_company.id,
    )
    db.add(cliente)
    db.commit()
    db.refresh(cliente)
    return cliente


@pytest.fixture
def tranca_exemplo(db, default_company):
    """
    Fixture para criar trança de exemplo
    """
    from app.models.tranca import Tranca
    from decimal import Decimal
    tranca = Tranca(
        nome="Box Braids",
        descricao="Tranças box braids clássicas",
        imagens=["http://localhost:8000/static/trancas/box-braids.png"],
        ativo=True,
        company_id=default_company.id,
    )
    db.add(tranca)
    db.commit()
    db.refresh(tranca)
    return tranca


@pytest.fixture
def service_image_exemplo(db, tranca_exemplo):
    """
    Fixture que sincroniza galeria da trança e retorna a primeira foto com ID.
    """
    from app.services.service_image_service import ServiceImageService
    from decimal import Decimal
    imagens = ServiceImageService(db).sincronizar_da_tranca(tranca_exemplo.id)
    assert len(imagens) >= 1
    img = imagens[0]
    img.valor_total = Decimal("150.00")
    img.duracao_minutos = 180
    img.percentual_sinal = Decimal("0.30")
    db.commit()
    db.refresh(img)
    return img


@pytest.fixture
def synced_catalog(db, tranca_exemplo, service_image_exemplo):
    """
    Sincroniza tranca/modelo legado para core_catalogs/core_offerings.

    Returns:
        Tupla (CoreCatalog, CoreOffering).
    """
    from app.modules.catalog.application.legacy_sync_service import LegacySyncService
    from app.modules.catalog.domain.models import CoreCatalog, CoreOffering

    LegacySyncService(db).sync_all()
    catalog = (
        db.query(CoreCatalog)
        .filter(CoreCatalog.legacy_tranca_id == tranca_exemplo.id)
        .first()
    )
    offering = (
        db.query(CoreOffering)
        .filter(CoreOffering.legacy_service_image_id == service_image_exemplo.id)
        .first()
    )
    assert catalog is not None
    assert offering is not None
    return catalog, offering


@pytest.fixture
def synced_scheduling(db, default_company, tranca_exemplo, service_image_exemplo):
    """
    Sincroniza metamodelo catalog + scheduling para testes v1.

    Returns:
        Dict com entidades core sincronizadas.
    """
    from app.modules.catalog.application.legacy_sync_service import LegacySyncService
    from app.modules.catalog.domain.models import CoreCatalog, CoreOffering
    from app.modules.scheduling.application.legacy_sync_service import (
        SchedulingLegacySyncService,
    )
    from app.modules.scheduling.domain.models import CoreLocation, CoreResource, CoreWorker

    LegacySyncService(db).sync_all()
    SchedulingLegacySyncService(db).sync_all()

    catalog = (
        db.query(CoreCatalog)
        .filter(CoreCatalog.legacy_tranca_id == tranca_exemplo.id)
        .first()
    )
    offering = (
        db.query(CoreOffering)
        .filter(CoreOffering.legacy_service_image_id == service_image_exemplo.id)
        .first()
    )
    location = (
        db.query(CoreLocation)
        .filter(
            CoreLocation.company_id == default_company.id,
            CoreLocation.is_default.is_(True),
        )
        .first()
    )
    resource = (
        db.query(CoreResource)
        .filter(
            CoreResource.company_id == default_company.id,
            CoreResource.is_default.is_(True),
        )
        .first()
    )
    worker = (
        db.query(CoreWorker)
        .filter(CoreWorker.company_id == default_company.id)
        .first()
    )

    assert catalog and offering and location and resource
    return {
        "catalog": catalog,
        "offering": offering,
        "location": location,
        "resource": resource,
        "worker": worker,
    }

