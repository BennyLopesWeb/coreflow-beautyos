# Sprint 22 — Prometheus DLQ + Canary Auto-Promote + Terraform Drift

## Entregas

| Item | Status |
|------|--------|
| Métricas Prometheus DLQ replay (`coreflow_dlq_replay_*`) | ✅ |
| `GET /metrics` + `GET /v1/events/dlq/metrics` | ✅ |
| `EasUpdateCanaryHealthService` — probe mock/live | ✅ |
| `EasUpdateCanaryPromoteService` — auto-promote após health | ✅ |
| `TerraformDriftService` — config hash + plan drift | ✅ |
| `scripts/terraform-drift.sh` + CI `terraform-drift.yml` | ✅ |
| Versão `1.12.0-sprint22` | ✅ |

## Prometheus DLQ Metrics

```bash
PROMETHEUS_ENABLED=true

GET /metrics
GET /v1/events/dlq/metrics
```

Métricas expostas:
- `coreflow_dlq_replay_total{mode,status}` — contador de replays
- `coreflow_dlq_replay_duration_seconds{mode}` — histograma de duração
- `coreflow_dlq_pending` — gauge pendentes
- `coreflow_dlq_eligible_now` — gauge elegíveis agora

Instrumentação em `KafkaDlqReplayService` e `DlqHandlerReplayService`.

## EAS Canary Auto-Promote

```yaml
mobile:
  update:
    canary_auto_promote: true
    canary_health:
      min_success_rate: 0.99
      min_samples: 10
```

```bash
GET /v1/mobile/eas/update/canary/beauty/health?segment=trancista
POST /v1/mobile/eas/update/canary/beauty/health/sample?segment=trancista&success=true
GET /v1/mobile/eas/update/canary/beauty/promote/evaluate?segment=trancista
POST /v1/mobile/eas/update/canary/beauty/promote?segment=trancista
POST .../promote?force=true   # admin, ignora health
```

Promoção gera `eas channel:edit {production} --branch {canary_branch}`.

Modo mock (`MOBILE_EAS_UPDATE_CANARY_HEALTH_LIVE=false`) usa amostras
registradas via API. Live faz probe HTTP no `probe_url` do manifest.

## Terraform Drift Detection

```bash
make terraform-drift-check
./scripts/terraform-drift.sh all config
./scripts/terraform-drift.sh dev plan   # requer TERRAFORM_DRIFT_LIVE=true

GET /v1/mobile/cdn/terraform/drift?environment=dev
GET /v1/mobile/cdn/terraform/drift/all
```

- **config drift**: compara hash SHA256 do tfvars exportado vs commitado
- **plan drift**: `terraform plan -detailed-exitcode` (CI workflow_dispatch)

GitHub Actions: `.github/workflows/terraform-drift.yml` falha PR se config drift.

## Próximo: CF-23

- Grafana dashboards as code para métricas DLQ
- Canary rollback automático em health degradation
- Terraform policy-as-code (OPA/Sentinel)
