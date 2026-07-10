# Sprint 23 — Grafana Dashboards + Canary Rollback + Terraform OPA

## Entregas

| Item | Status |
|------|--------|
| `GrafanaDashboardService` — dashboard DLQ as code | ✅ |
| `infra/grafana/dashboards/coreflow-dlq.json` + provisioning | ✅ |
| `EasUpdateCanaryRollbackService` — auto-rollback | ✅ |
| `TerraformPolicyService` — OPA/Sentinel embedded + live | ✅ |
| `infra/terraform/policies/cdn.rego` | ✅ |
| CI `terraform-policy.yml` + scripts | ✅ |
| Versão `1.13.0-sprint23` | ✅ |

## Grafana Dashboards as Code

```bash
make grafana-export
./scripts/grafana-export.sh

GET /v1/events/grafana/dashboard/dlq
GET /v1/events/grafana/dashboard/dlq/document
POST /v1/events/grafana/dashboard/dlq/export
```

Exporta:
- `infra/grafana/dashboards/coreflow-dlq.json`
- `infra/grafana/provisioning/datasources/prometheus.yaml`
- `infra/grafana/provisioning/dashboards/coreflow.yaml`

Panels: DLQ pending, eligible, replay rate by status/mode, p95 duration.

## Canary Auto-Rollback

```yaml
mobile:
  update:
    canary_auto_rollback: true
    canary_health:
      rollback_threshold: 0.95
      rollback_min_samples: 5
```

```bash
GET /v1/mobile/eas/update/canary/beauty/rollback/evaluate?segment=trancista
POST /v1/mobile/eas/update/canary/beauty/rollback?segment=trancista
POST .../rollback?force=true
```

Após `auto_promote`, branch production anterior é registrado.
Se `success_rate < rollback_threshold`, gera
`eas channel:edit {production} --branch {previous_branch}`.

## Terraform Policy-as-Code (OPA)

```bash
make terraform-policy-check
./scripts/terraform-policy.sh all
./scripts/terraform-policy.sh prod

GET /v1/mobile/cdn/terraform/policy
GET /v1/mobile/cdn/terraform/policy/dev
GET /v1/mobile/cdn/terraform/policy/all/evaluate
```

Regras embarcadas (CI padrão):
- prod → `PriceClass_All`, bucket `-prod`
- staging → bucket `-staging`
- dev → bucket `-dev`
- `tags.Environment` == ambiente
- `tenant_behaviors` não vazio

Modo live: `TERRAFORM_OPA_LIVE=true` usa `opa eval` + `cdn.rego`.

## Próximo: CF-24

- Alertmanager rules as code para DLQ
- Canary rollback worker loop automático
- Terraform Sentinel enterprise policies
