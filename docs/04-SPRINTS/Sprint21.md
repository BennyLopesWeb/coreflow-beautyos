# Sprint 21 — DLQ Handler Replay + EAS Canary + Terraform Pipeline

## Entregas

| Item | Status |
|------|--------|
| `DlqHandlerReplayService` — replay handler-aware via `event_bus` | ✅ |
| Modo `handler` \| `republish` (`KAFKA_DLQ_REPLAY_MODE`) | ✅ |
| `POST /v1/events/dlq/replay-auto?mode=handler` | ✅ |
| `EasUpdateCanaryService` — OTA canary por segmento | ✅ |
| `GET /v1/mobile/eas/update/canary/{plugin_id}` | ✅ |
| `TerraformPipelineService` — dev → staging → prod | ✅ |
| `scripts/terraform-pipeline.sh` | ✅ |
| Manifests com `canary_percentage` / `canary_segments` | ✅ |
| Versão `1.11.0-sprint21` | ✅ |

## DLQ Handler-Aware Replay

Reprocessa mensagens DLQ in-process via `event_bus.publish`, marcando
outbox associado como `PROCESSED` quando `outbox_id` está no envelope.

```bash
KAFKA_DLQ_REPLAY_MODE=handler   # default CF-21
KAFKA_DLQ_REPLAY_MODE=republish # CF-20 Kafka republish

POST /v1/events/dlq/replay-auto?limit=20&mode=handler
POST /v1/events/dlq/{id}/replay?mode=handler&force=true
```

Worker `dlq_replay_worker` usa `DlqHandlerReplayService` por padrão.

## EAS Update Canary por Segmento

```yaml
mobile:
  update:
    canary_percentage: 10
    canary_segments:
      - trancista
      - futebol
```

```bash
GET /v1/mobile/eas/update/canary/beauty?segment=trancista
GET /v1/mobile/eas/update/canary/sports/segments
```

Cada segmento recebe channel `{plugin_id}-canary-{segment}` e comando
`eas update` com `--rollout-percentage`.

## Terraform Multi-Environment Pipeline

```bash
make terraform-pipeline-export
make terraform-pipeline-plan
./scripts/terraform-pipeline.sh apply-all
GET /v1/mobile/cdn/terraform/pipeline
POST /v1/mobile/cdn/terraform/pipeline/export
```

Ambientes com overrides:

| Env | Bucket suffix | Price class | Approval |
|-----|---------------|-------------|----------|
| dev | `-dev` | PriceClass_100 | não |
| staging | `-staging` | PriceClass_100 | sim |
| prod | `-prod` | PriceClass_All | sim |

Gera `infra/terraform/pipeline.json` com ordem de promoção.

## Próximo: CF-22

- DLQ replay com métricas Prometheus
- EAS canary auto-promote após health check
- Terraform drift detection CI
