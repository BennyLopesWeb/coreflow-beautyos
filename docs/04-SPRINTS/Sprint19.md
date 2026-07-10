# Sprint 19 — EAS Update OTA + Kafka DLQ + Terraform CDN

## Entregas

| Item | Status |
|------|--------|
| `EasUpdateService` — canais OTA por plugin | ✅ |
| `mobile.update:` nos manifests | ✅ |
| `frontend/eas.update.json` + `scripts/eas-update.sh` | ✅ |
| `CoreEventDlq` + `KafkaDlqService` | ✅ |
| Kafka consumer → DLQ em falhas de schema/handler | ✅ |
| `GET /v1/events/dlq` + `/dlq/stats` + replay | ✅ |
| Módulo Terraform `infra/terraform/modules/coreflow-cdn` | ✅ |
| `TerraformExportService` → `terraform.tfvars.json` | ✅ |
| Versão `1.9.0-sprint19` | ✅ |

## EAS Update OTA por plugin

```yaml
mobile:
  update:
    runtime_version: "1.0.0"
    preview_channel: sports-preview
    production_channel: sports-production
```

```bash
make eas-update-generate
GET /v1/mobile/eas/update/channels
./scripts/eas-update.sh sports preview "Fix deep links"
```

Canais alinhados aos builds white-label CF-17.

## Kafka Dead-Letter Queue

```bash
KAFKA_DLQ_ENABLED=true
KAFKA_DLQ_TOPIC=coreflow.events.dlq

GET /v1/events/dlq
GET /v1/events/dlq/stats
POST /v1/events/dlq/{id}/replay
```

Motivos: `schema_incompatible`, `avro_decode_error`, `envelope_parse_error`, `handler_error`.

Mensagens poison pill são commitadas após DLQ (evita loop infinito).

## Terraform CDN + CloudFront

```bash
make export-terraform-cdn
POST /v1/mobile/cdn/terraform/export?environment=dev

cd infra/terraform/environments/dev
terraform init
terraform plan -var-file=terraform.tfvars.json
```

Módulo: `infra/terraform/modules/coreflow-cdn`
- S3 bucket privado + OAC
- CloudFront com `ordered_cache_behavior` por plugin

## Concluído em CF-20

Ver [`Sprint20.md`](./Sprint20.md).
