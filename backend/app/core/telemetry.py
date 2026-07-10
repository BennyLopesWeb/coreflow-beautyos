"""
OpenTelemetry — observabilidade opcional CoreFlow Platform.

Ative com ``OTEL_ENABLED=true``. Export OTLP requer collector externo.
"""
from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger("telemetry")


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
