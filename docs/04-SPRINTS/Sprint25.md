# Sprint 25 — PagerDuty/Opsgenie + Canary DB Persist + Terraform Cloud

## Entregas

| Item | Status |
|------|--------|
| Receivers PagerDuty + Opsgenie no Alertmanager | ✅ |
| `CoreCanaryPromotion` + migration `cf010` | ✅ |
| `CanaryPromotionRepository` — persistência DB | ✅ |
| Worker rollback lê promoções do banco | ✅ |
| `TerraformCloudPolicyService` — policy set TFC | ✅ |
| CI `terraform-cloud-policy.yml` | ✅ |
| Versão `1.15.0-sprint25` | ✅ |

## PagerDuty / Opsgenie (Alertmanager)

```bash
ALERTMANAGER_PAGERDUTY_ENABLED=true
ALERTMANAGER_PAGERDUTY_ROUTING_KEY=...
ALERTMANAGER_OPSGENIE_ENABLED=true
ALERTMANAGER_OPSGENIE_API_KEY=...

make alertmanager-export
```

Receivers adicionados:
- `coreflow-pagerduty` — Events API v2, rota severity=critical
- `coreflow-opsgenie` — P1 critical / P3 warning

## Canary Rollback Persistido (DB)

```bash
MOBILE_EAS_UPDATE_CANARY_PERSIST_DB=true

GET /v1/mobile/eas/update/canary/promotions
POST /v1/mobile/eas/update/canary/rollback/scan
```

Tabela `core_canary_promotions`:
- Sobrevive restart worker/API
- Migration Alembic `cf010_canary_promotions`
- Worker usa `SessionLocal()` + repositório

## Terraform Cloud Policy Set

```bash
make terraform-cloud-policy-export
./scripts/terraform-cloud-policy.sh

GET /v1/mobile/cdn/terraform/cloud/policy-set
POST /v1/mobile/cdn/terraform/cloud/policy-set/export
GET /v1/mobile/cdn/terraform/cloud/evaluate
```

Exporta `infra/terraform/cloud/policy-set.json`:
- 6 policies (OPA + Sentinel × dev/staging/prod)
- Enforcement: advisory → soft-mandatory → mandatory
- Validação local OPA + Sentinel antes do sync TFC

## Próximo: CF-26

- Slack receivers Alertmanager
- Canary promotion history audit log
- Terraform Cloud run task automation
