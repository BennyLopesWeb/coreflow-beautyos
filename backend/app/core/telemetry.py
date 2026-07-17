"""
OpenTelemetry — observabilidade opcional CoreFlow Platform.

Ative com ``OTEL_ENABLED=true``. Export OTLP requer collector externo.
"""
from contextlib import contextmanager
from typing import Any, Iterator

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger("telemetry")


class _NoOpSpan:
    """
    Span no-op quando OTEL está desligado ou indisponível.

    Methods:
        set_attribute: Ignora atributos.
        __enter__/__exit__: Context manager neutro.
    """

    def set_attribute(self, key: str, value: Any) -> None:
        """
        No-op — não registra atributo.

        Args:
            key: Nome do atributo.
            value: Valor.

        Returns:
            None
        """
        return None

    def __enter__(self) -> "_NoOpSpan":
        """
        Entra no context manager.

        Returns:
            self
        """
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        """
        Sai do context manager sem suprimir exceções.

        Returns:
            False
        """
        return False


class _NoOpTracer:
    """
    Tracer no-op compatível com a API ``start_as_current_span``.
    """

    def start_as_current_span(self, name: str) -> _NoOpSpan:
        """
        Retorna span no-op.

        Args:
            name: Nome do span (ignorado).

        Returns:
            _NoOpSpan
        """
        return _NoOpSpan()


def get_tracer(name: str = "coreflow"):
    """
    Obtém tracer OpenTelemetry ou no-op seguro.

    Args:
        name: Nome lógico do tracer (ex.: ``booking``).

    Returns:
        Tracer OTEL ou ``_NoOpTracer`` se flag OFF / pacote ausente.
    """
    if not settings.OTEL_ENABLED:
        return _NoOpTracer()
    try:
        from opentelemetry import trace

        return trace.get_tracer(name)
    except ImportError:
        return _NoOpTracer()


@contextmanager
def booking_create_core_span(
    company_id: int,
    catalog_id: int,
    offering_id: int,
) -> Iterator[Any]:
    """
    Abre span ``booking.create.core`` no path domain (FF-OBS-001 / R2-F5).

    Args:
        company_id: Tenant.
        catalog_id: Catalog.
        offering_id: Offering.

    Yields:
        Span ativo (OTEL ou no-op).
    """
    tracer = get_tracer("booking")
    with tracer.start_as_current_span("booking.create.core") as span:
        span.set_attribute("booking.company_id", company_id)
        span.set_attribute("booking.catalog_id", catalog_id)
        span.set_attribute("booking.offering_id", offering_id)
        yield span


def setup_telemetry(app) -> None:
    """
    Configura tracing OpenTelemetry na aplicação FastAPI.

    No-op quando ``OTEL_ENABLED`` é False ou pacotes não instalados.

    Args:
        app: Instância FastAPI.

    Returns:
        None
    """
    if not settings.OTEL_ENABLED:
        return

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    except ImportError:
        logger.warning("OpenTelemetry não instalado — pip install opentelemetry-*")
        return

    resource = Resource.create(
        {
            "service.name": settings.OTEL_SERVICE_NAME,
            "service.version": settings.APP_VERSION,
        }
    )
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    trace.set_tracer_provider(provider)

    FastAPIInstrumentor.instrument_app(app, excluded_urls="health,docs,redoc,openapi.json")
    logger.info(f"OpenTelemetry ativo — service={settings.OTEL_SERVICE_NAME}")
