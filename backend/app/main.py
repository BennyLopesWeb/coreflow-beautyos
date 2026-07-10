"""
Aplicação principal FastAPI
Configuração e registro de routers
"""
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from fastapi.responses import Response
from pathlib import Path
from app.core.config import settings
from app.core.logging_config import get_logger
from app.core.legacy_sunset import LegacySunsetMiddleware
from app.core.core_enforcement import CoreEnforcementMiddleware, resolve_enforcement_mode
from app.core.error_handler import (
    trancapro_exception_handler,
    validation_exception_handler,
    general_exception_handler
)
from app.modules.identity.api.auth_router import router as auth_router
from app.modules.identity.api.companies_router import router as companies_router
from app.routers import trancas, agendamentos, pagamentos, fila, financeiro, webhook, clientes, notifications, admin, reservations, queue, payments, plugins, v1_catalogs, v1_bookings, v1_scheduling, v1_customers, v1_payments, v1_waitlist, v1_ai, v1_workflows, v1_orders, v1_invoices, v1_assets, v1_inventory, v1_marketplace, v1_devices, v1_outbox, v1_mobile, v1_events, v1_platform, well_known
from app.core.legacy_telemetry import LegacyTelemetryMiddleware
from app.core.telemetry import setup_telemetry

logger = get_logger("main")

# Cria aplicação FastAPI
app = FastAPI(
    title=settings.APP_NAME,
    description="CoreFlow Platform — Build Once. Configure Everywhere. (BeautyOS = plugin beauty)",
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configura CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Depreciação rotas legado (RFC 8594)
app.add_middleware(LegacySunsetMiddleware, enabled=settings.LEGACY_SUNSET_ENABLED)

# Enforcement escritas legado → v1 (Fase B: off | warn | block)
app.add_middleware(
    CoreEnforcementMiddleware,
    mode=resolve_enforcement_mode(),
)

# Telemetria HTTP por camada API (R1-F1)
app.add_middleware(LegacyTelemetryMiddleware)

# OpenTelemetry (opcional)
setup_telemetry(app)

# Registra handlers de exceção
app.add_exception_handler(HTTPException, trancapro_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# Registra routers
app.include_router(auth_router)
app.include_router(companies_router)
app.include_router(plugins.router)
app.include_router(v1_catalogs.router)
app.include_router(v1_bookings.router)
app.include_router(v1_customers.router)
app.include_router(v1_payments.router)
app.include_router(v1_waitlist.router)
app.include_router(v1_ai.router)
app.include_router(v1_workflows.router)
app.include_router(v1_orders.router)
app.include_router(v1_invoices.router)
app.include_router(v1_assets.router)
app.include_router(v1_inventory.router)
app.include_router(v1_marketplace.router)
app.include_router(v1_devices.router)
app.include_router(v1_outbox.router)
app.include_router(v1_mobile.router)
app.include_router(v1_events.router)
app.include_router(v1_platform.router)
app.include_router(well_known.router)
app.include_router(v1_scheduling.locations_router)
app.include_router(v1_scheduling.workers_router)
app.include_router(v1_scheduling.resources_router)
app.include_router(v1_scheduling.scheduling_router)
app.include_router(clientes.router)
app.include_router(trancas.router)
app.include_router(agendamentos.router)
app.include_router(pagamentos.router)
app.include_router(fila.router)
app.include_router(financeiro.router)
app.include_router(webhook.router)
app.include_router(notifications.router)
app.include_router(admin.router)
app.include_router(reservations.router)
app.include_router(queue.router)
app.include_router(payments.router)

# Arquivos estáticos (imagens de tranças)
_static_dir = Path(__file__).resolve().parents[1] / "static"
if _static_dir.is_dir():
    app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")

# CDN estático .well-known exportado (CF-15)
_cdn_dir = Path(__file__).resolve().parents[1] / "cdn"
if _cdn_dir.is_dir():
    app.mount("/cdn-static", StaticFiles(directory=str(_cdn_dir)), name="cdn-static")


@app.get("/")
def root():
    """
    Endpoint raiz
    Retorna informações básicas da API
    """
    return {
        "platform": settings.PLATFORM_NAME,
        "message": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "plugins": "/v1/plugins",
        "status": "ok",
    }


@app.get("/health")
def health_check():
    """
    Health check endpoint
    Usado para verificar se a API está funcionando
    """
    return {"status": "healthy"}


@app.get(settings.PROMETHEUS_METRICS_PATH)
def prometheus_metrics():
    """
    Endpoint Prometheus text exposition (CF-22).

    Returns:
        Métricas no formato Prometheus ou 503 se desabilitado.
    """
    from app.core.prometheus_metrics import render_prometheus
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        body = render_prometheus(db)
        return Response(
            content=body,
            media_type="text/plain; version=0.0.4; charset=utf-8",
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    finally:
        db.close()


@app.on_event("startup")
def startup_event():
    """
    Evento executado ao iniciar a aplicação
    Inicializa banco de dados se necessário
    """
    from app.db.init_db import init_db
    init_db()

    from app.modules.booking.application.handlers import register_booking_handlers
    register_booking_handlers()

    from app.modules.workflow.application.handlers import register_workflow_handlers
    register_workflow_handlers()

    from app.modules.identity.application.handlers import register_identity_handlers
    register_identity_handlers()

    from app.modules.push.application.handlers import register_push_handlers
    register_push_handlers()

    from app.core.plugin.registry import plugin_registry
    loaded = plugin_registry.load_all()
    logger.info(f"CoreFlow: {loaded} plugin(s) carregado(s)")
    print(f"🔌 CoreFlow: {loaded} plugin(s) carregado(s)")

    logger.info(f"{settings.PLATFORM_NAME} — {settings.APP_NAME} v{settings.APP_VERSION} iniciado!")
    print(f"🚀 {settings.PLATFORM_NAME} — {settings.APP_NAME} v{settings.APP_VERSION} iniciado!")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Middleware para logar todas as requisições
    """
    logger.info(
        f"{request.method} {request.url.path}",
        extra={
            "method": request.method,
            "path": request.url.path,
            "client": request.client.host if request.client else None
        }
    )
    
    response = await call_next(request)
    
    logger.info(
        f"{request.method} {request.url.path} - {response.status_code}",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code
        }
    )
    
    return response
