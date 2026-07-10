"""
Router API v1 — Event Schema Registry (CF-15/16/17).
"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.config import settings
from app.db.session import get_db
from app.modules.identity.api.deps import get_current_admin_user
from app.models.user import User
from app.shared.events.confluent_schema_registry import ConfluentSchemaRegistryClient
from app.shared.events.schema_registry import get_schema_registry
from sqlalchemy.orm import Session

router = APIRouter(prefix="/v1/events", tags=["CoreFlow — Event Schemas"])


@router.get("/schemas", response_model=List[Dict[str, Any]])
def listar_schemas():
    """
    Lista JSON Schemas registrados para eventos Kafka.

    Returns:
        Lista de schema_id, title e campos required.
    """
    return get_schema_registry().list_schemas()


@router.get("/schemas/avro")
def listar_schemas_avro() -> List[Dict[str, Any]]:
    """
    Lista schemas Avro locais (.avsc) para eventos Kafka.

    Returns:
        Lista de schema_id e record name Avro.
    """
    from app.shared.events.avro_codec import AvroEventCodec

    return AvroEventCodec().list_schemas()


@router.get("/schemas/avro/coverage")
def avro_coverage() -> List[Dict[str, Any]]:
    """
    Cobertura Avro vs JSON Schema por evento.

    Returns:
        Lista indicando has_json/has_avro por schema_id.
    """
    return get_schema_registry().list_avro_coverage()


@router.post("/schemas/avro/register-all")
def register_all_avro(
    _: User = Depends(get_current_admin_user),
) -> List[Dict[str, Any]]:
    """
    Registra todos os schemas Avro no Confluent Schema Registry (admin).

    Returns:
        Lista de subjects registrados com confluent_schema_id.
    """
    try:
        return get_schema_registry().register_all_avro_to_confluent()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/schemas/avro/evolution")
def avro_evolution_report() -> List[Dict[str, Any]]:
    """
    Relatório de evolução Avro e compatibilidade BACKWARD (CF-18).

    Returns:
        Lista de event_types com versões e status compatible.
    """
    from app.shared.events.avro_evolution_service import AvroEvolutionService

    return AvroEvolutionService().evolution_report()


@router.get("/schemas/avro/{event_type}/versions")
def avro_event_versions(event_type: str) -> List[Dict[str, Any]]:
    """
    Lista versões Avro de um event_type.

    Args:
        event_type: Ex.: booking.approved

    Returns:
        Versões ordenadas com schema_id.
    """
    from app.shared.events.avro_evolution_service import AvroEvolutionService

    return AvroEvolutionService().list_event_versions(event_type)


@router.post("/schemas/avro/check-compatibility")
def check_avro_compatibility(
    old_schema_id: str = Query(..., description="Schema anterior, ex.: booking.approved.v1"),
    new_schema_id: str = Query(..., description="Schema novo, ex.: booking.approved.v2"),
) -> Dict[str, Any]:
    """
    Verifica compatibilidade BACKWARD entre duas versões Avro.

    Args:
        old_schema_id: Schema anterior (query param).
        new_schema_id: Schema novo (query param).

    Returns:
        Resultado do check local de compatibilidade.
    """
    from app.shared.events.avro_evolution_service import AvroEvolutionService

    return AvroEvolutionService().check_backward_compatible(old_schema_id, new_schema_id)


@router.post("/schemas/avro/register-evolved")
def register_evolved_avro(
    event_type: str = Query(..., description="Ex.: booking.approved"),
    schema_id: Optional[str] = Query(None, description="Versão específica ou latest"),
    _: User = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """
    Registra versão evoluída Avro no Confluent após check (admin).

    Args:
        event_type: Ex.: booking.approved
        schema_id: Versão específica ou latest.

    Returns:
        Resultado do registro Confluent.
    """
    from app.shared.events.avro_evolution_service import AvroEvolutionService

    try:
        return AvroEvolutionService().register_evolved_schema(event_type, schema_id)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/schemas/{schema_id}")
def obter_schema(schema_id: str) -> Dict[str, Any]:
    """
    Obtém JSON Schema completo por ID.

    Args:
        schema_id: Ex.: booking.approved.v1

    Returns:
        JSON Schema document.
    """
    schema = get_schema_registry().get_schema(schema_id)
    if not schema:
        raise HTTPException(status_code=404, detail=f"Schema '{schema_id}' não encontrado")
    return schema


@router.get("/schema-registry/health")
def schema_registry_health() -> Dict[str, Any]:
    """
    Health check do Confluent Schema Registry (quando mode=confluent).

    Returns:
        Status e URL do registry.
    """
    mode = settings.KAFKA_SCHEMA_REGISTRY_MODE
    if mode != "confluent":
        return {
            "mode": mode,
            "status": "ok",
            "message": "File-based schema registry (local JSON)",
        }
    client = ConfluentSchemaRegistryClient()
    healthy = client.health_check()
    return {
        "mode": "confluent",
        "url": settings.KAFKA_SCHEMA_REGISTRY_URL,
        "status": "ok" if healthy else "unreachable",
        "encoding": settings.KAFKA_SCHEMA_ENCODING,
    }


@router.get("/dlq")
def list_dlq_entries(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """
    Lista entradas recentes da dead-letter queue Kafka (CF-19).

    Args:
        limit: Máximo de registros.

    Returns:
        Lista de mensagens DLQ persistidas.
    """
    from app.shared.events.kafka_dlq import KafkaDlqService

    return KafkaDlqService(db).list_recent(limit=limit)


@router.get("/dlq/stats")
def dlq_stats(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Estatísticas agregadas da DLQ Kafka.

    Returns:
        Total, contagem por reason e pendentes de replay.
    """
    from app.shared.events.kafka_dlq import KafkaDlqService

    return KafkaDlqService(db).stats()


@router.get("/dlq/metrics")
def dlq_metrics(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Resumo JSON das métricas Prometheus DLQ replay (CF-22).

    Returns:
        Dict com gauges DLQ e contadores de replay.
    """
    from app.core.prometheus_metrics import metrics_summary

    return metrics_summary(db)


@router.get("/grafana/dashboard/dlq")
def grafana_dlq_dashboard_preview() -> Dict[str, Any]:
    """
    Preview do dashboard Grafana DLQ as code (CF-23).

    Returns:
        Manifest uid, panels e comando de export.
    """
    from app.modules.observability.application.grafana_dashboard_service import GrafanaDashboardService

    return GrafanaDashboardService().manifest()


@router.get("/grafana/dashboard/dlq/document")
def grafana_dlq_dashboard_document() -> Dict[str, Any]:
    """
    Documento JSON completo do dashboard DLQ Grafana.

    Returns:
        Dashboard Grafana 9+ serializável.
    """
    from app.modules.observability.application.grafana_dashboard_service import GrafanaDashboardService

    return GrafanaDashboardService().dlq_dashboard_document()


@router.post("/grafana/dashboard/dlq/export")
def export_grafana_dlq_dashboard(
    _: User = Depends(get_current_admin_user),
) -> Dict[str, str]:
    """
    Exporta dashboard + provisioning para infra/grafana/ (CF-23).

    Returns:
        Paths dos arquivos exportados.
    """
    from app.modules.observability.application.grafana_dashboard_service import GrafanaDashboardService

    return GrafanaDashboardService().export_all()


@router.get("/alertmanager/dlq")
def alertmanager_dlq_manifest() -> Dict[str, Any]:
    """
    Preview das regras Alertmanager/Prometheus DLQ (CF-24).

    Returns:
        Manifest com rule names, thresholds e export command.
    """
    from app.modules.observability.application.alertmanager_rules_service import AlertmanagerRulesService

    return AlertmanagerRulesService().manifest()


@router.get("/alertmanager/dlq/rules")
def alertmanager_dlq_rules() -> Dict[str, Any]:
    """
    Documento YAML de alerting rules Prometheus para DLQ.

    Returns:
        Dict groups/rules serializável.
    """
    from app.modules.observability.application.alertmanager_rules_service import AlertmanagerRulesService

    return AlertmanagerRulesService().prometheus_alert_rules()


@router.post("/alertmanager/dlq/export")
def export_alertmanager_dlq_rules(
    _: User = Depends(get_current_admin_user),
) -> Dict[str, str]:
    """
    Exporta rules Prometheus + alertmanager.yml (CF-24).

    Returns:
        Paths dos arquivos exportados.
    """
    from app.modules.observability.application.alertmanager_rules_service import AlertmanagerRulesService

    return AlertmanagerRulesService().export_all()


@router.post("/dlq/replay-auto")
def replay_dlq_auto(
    limit: int = Query(20, ge=1, le=200),
    force: bool = Query(False, description="Ignorar backoff exponencial"),
    mode: Optional[str] = Query(None, description="republish | handler"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """
    Executa replay automático em lote com backoff (CF-20/21).

    Args:
        limit: Máximo de mensagens por batch.
        force: Ignorar next_replay_at.
        mode: republish (Kafka) ou handler (event_bus in-process).

    Returns:
        Resumo success/failed/scheduled.
    """
    from app.shared.events.dlq_handler_replay import DlqHandlerReplayService

    return DlqHandlerReplayService(db).replay_batch(limit=limit, force=force, mode=mode)


@router.post("/dlq/{dlq_id}/replay")
def replay_dlq_entry(
    dlq_id: int,
    force: bool = Query(False, description="Ignorar backoff"),
    mode: Optional[str] = Query(None, description="republish | handler"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """
    Replay manual de uma entrada DLQ (CF-20/21).

    Args:
        dlq_id: ID do registro DLQ.
        force: Ignorar next_replay_at.
        mode: republish | handler.

    Returns:
        Resultado do replay (success|failed|scheduled).
    """
    from app.shared.events.dlq_handler_replay import DlqHandlerReplayService

    try:
        return DlqHandlerReplayService(db).replay_one(dlq_id, force=force, mode=mode)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
