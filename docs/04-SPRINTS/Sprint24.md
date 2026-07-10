# Sprint 24 — Alertmanager + Canary Rollback Worker + Terraform Sentinel

## Entregas

| Item | Status |
|------|--------|
| `AlertmanagerRulesService` — rules Prometheus + config Alertmanager | ✅ |
| `infra/prometheus/rules/coreflow-dlq.yml` | ✅ |
| `canary_rollback_worker` — loop automático de rollback | ✅ |
| `EasUpdateCanaryRollbackService.scan_and_rollback()` | ✅ |
| `TerraformSentinelService` — políticas enterprise | ✅ |
| `infra/terraform/policies/sentinel/cdn.sentinel` | ✅ |
| CI `terraform-sentinel.yml` | ✅ |
| Versão `1.14.0-sprint24` | ✅ |

## Alertmanager Rules as Code

```bash
make alertmanager-export
./scripts/alertmanager-export.sh

GET /v1/events/alertmanager/dlq
GET /v1/events/alertmanager/dlq/rules
POST /v1/events/alertmanager/dlq/export
```

Alertas exportados:
- `CoreFlowDLQPendingHigh` — pending > threshold (5m)
- `CoreFlowDLQEligibleHigh` — elegíveis imediatos (2m)
- `CoreFlowDLQReplayFailureRateHigh` — taxa de falha replay
- `CoreFlowDLQReplayStalled` — backlog sem replay success (30m)

Config Alertmanager com rotas `critical` e `dlq` + webhooks.

## Canary Rollback Worker Loop

```bash
make canary-rollback-once
make canary-rollback-loop

POST /v1/mobile/eas/update/canary/rollback/scan
python -m app.workers.canary_rollback_worker --mode loop --interval 120
```

Docker: `docker-compose.cdn.yml` → serviço `canary-rollback-worker`.

Varre promoções ativas registradas após `auto_promote` e executa
rollback quando `success_rate < rollback_threshold`.

## Terraform Sentinel Enterprise

```bash
make terraform-sentinel-check
./scripts/terraform-sentinel.sh all

GET /v1/mobile/cdn/terraform/sentinel
GET /v1/mobile/cdn/terraform/sentinel/prod
GET /v1/mobile/cdn/terraform/sentinel/all/evaluate
```

Regras enterprise (embarcadas + `cdn.sentinel`):
- Tags obrigatórias prod: Environment, Component, Version, CostCenter, Owner
- prod → PriceClass_All, aliases não vazio
- Remote state encrypt + DynamoDB lock (staging/prod)
- Limites max aliases/behaviors, min TTL prod

Tags enterprise injetadas em `TerraformPipelineService.tfvars_for_environment`.

## Próximo: CF-25

- PagerDuty/Opsgenie receivers Alertmanager
- Canary rollback persistido em DB (survive restart)
- Terraform Cloud policy set integration
