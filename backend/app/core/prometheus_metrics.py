"""
Prometheus metrics — observabilidade CoreFlow Platform (CF-22).

Expõe contadores/gauges para DLQ replay e endpoint ``/metrics`` quando
``PROMETHEUS_ENABLED=true``.
"""
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger("prometheus_metrics")

_metrics_available = False
_dlq_replay_total = None
_dlq_replay_duration = None
_dlq_pending_gauge = None
_dlq_eligible_gauge = None
_http_requests_total = None
_http_request_duration = None


def _init_metrics() -> bool:
    """
    Inicializa métricas Prometheus (lazy import).

    Returns:
        True se prometheus_client está disponível e métricas foram criadas.
    """
    global _metrics_available, _dlq_replay_total, _dlq_replay_duration
    global _dlq_pending_gauge, _dlq_eligible_gauge
    global _http_requests_total, _http_request_duration

    if _metrics_available:
        return True

    if not settings.PROMETHEUS_ENABLED:
        return False

    try:
        from prometheus_client import Counter, Gauge, Histogram

        _dlq_replay_total = Counter(
            "coreflow_dlq_replay_total",
            "Total de tentativas de replay DLQ",
            ["mode", "status"],
        )
        _dlq_replay_duration = Histogram(
            "coreflow_dlq_replay_duration_seconds",
            "Duração de replay DLQ individual",
            ["mode"],
            buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
        )
        _dlq_pending_gauge = Gauge(
            "coreflow_dlq_pending",
            "Mensagens DLQ pendentes de replay",
        )
        _dlq_eligible_gauge = Gauge(
            "coreflow_dlq_eligible_now",
            "Mensagens DLQ elegíveis para replay imediato",
        )
        _http_requests_total = Counter(
            "coreflow_http_requests_total",
            "Total de requisições HTTP por camada API",
            ["layer", "method", "status_class"],
        )
        _http_request_duration = Histogram(
            "coreflow_http_request_duration_seconds",
            "Duração de requisições HTTP por camada",
            ["layer", "method"],
            buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
        )
        _metrics_available = True
        return True
    except ImportError:
        logger.warning("prometheus_client não instalado — métricas desabilitadas")
        return False


def record_dlq_replay(mode: str, status: str, duration_seconds: Optional[float] = None) -> None:
    """
    Registra resultado de uma tentativa de replay DLQ.

    Args:
        mode: Modo de replay (handler | republish).
        status: success | failed | scheduled | skipped.
        duration_seconds: Duração opcional em segundos.

    Returns:
        None
    """
    if not _init_metrics() or _dlq_replay_total is None:
        return

    _dlq_replay_total.labels(mode=mode, status=status).inc()
    if duration_seconds is not None and _dlq_replay_duration is not None:
        _dlq_replay_duration.labels(mode=mode).observe(duration_seconds)


def record_http_request(
    layer: str,
    method: str,
    status_class: str,
    duration_seconds: float,
) -> None:
    """
    Registra requisição HTTP para telemetria legado/core (R1-F1).

    Args:
        layer: legacy | beautyos | core | identity | platform | other.
        method: Método HTTP.
        status_class: 2xx | 4xx | 5xx | other.
        duration_seconds: Duração em segundos.

    Returns:
        None
    """
    if not _init_metrics() or _http_requests_total is None:
        return

    _http_requests_total.labels(
        layer=layer,
        method=method,
        status_class=status_class,
    ).inc()
    if _http_request_duration is not None:
        _http_request_duration.labels(layer=layer, method=method).observe(duration_seconds)


def refresh_dlq_gauges(db: Session) -> None:
    """
    Atualiza gauges DLQ a partir do banco.

    Args:
        db: Sessão SQLAlchemy.

    Returns:
        None
    """
    if not _init_metrics() or _dlq_pending_gauge is None:
        return

    from app.shared.events.kafka_dlq import KafkaDlqService

    stats = KafkaDlqService(db).stats()
    _dlq_pending_gauge.set(stats.get("pending_replay", 0))
    _dlq_eligible_gauge.set(stats.get("eligible_now", 0))


def metrics_summary(db: Optional[Session] = None) -> Dict[str, Any]:
    """
    Resumo JSON das métricas DLQ (útil para testes e dashboards leves).

    Args:
        db: Sessão opcional para gauges derivados do banco.

    Returns:
        Dict com enabled, dlq stats e contadores se disponíveis.
    """
    from app.shared.events.kafka_dlq import KafkaDlqService

    summary: Dict[str, Any] = {
        "enabled": settings.PROMETHEUS_ENABLED,
        "prometheus_client_installed": _init_metrics(),
    }

    if db is not None:
        summary["dlq"] = KafkaDlqService(db).stats()

    if _metrics_available and _dlq_replay_total is not None:
        summary["counters"] = {
            "coreflow_dlq_replay_total": _collect_counter_samples(_dlq_replay_total),
        }

    return summary


def _collect_counter_samples(counter) -> list:
    """
    Coleta amostras de um Counter Prometheus para JSON.

    Args:
        counter: Instância prometheus_client.Counter.

    Returns:
        Lista de dicts label/value.
    """
    samples = []
    for metric in counter.collect():
        for sample in metric.samples:
            if sample.name.endswith("_total"):
                samples.append({"labels": sample.labels, "value": sample.value})
    return samples


def render_prometheus(db: Optional[Session] = None) -> bytes:
    """
    Renderiza métricas no formato Prometheus text exposition.

    Args:
        db: Sessão opcional para atualizar gauges antes da exportação.

    Returns:
        Bytes no formato Prometheus ou mensagem vazia se desabilitado.

    Raises:
        RuntimeError: Prometheus desabilitado ou pacote ausente.
    """
    if not settings.PROMETHEUS_ENABLED:
        raise RuntimeError("Prometheus desabilitado")

    if not _init_metrics():
        raise RuntimeError("prometheus_client não disponível")

    if db is not None:
        refresh_dlq_gauges(db)

    from prometheus_client import generate_latest

    return generate_latest()
