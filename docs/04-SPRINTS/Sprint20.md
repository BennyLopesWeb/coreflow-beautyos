# Sprint 20 — DLQ Replay Backoff + EAS Rollout + Terraform Remote State

## Entregas

| Item | Status |
|------|--------|
| `KafkaDlqReplayService` — replay automático com backoff exponencial | ✅ |
| Colunas `replay_attempts`, `next_replay_at`, `last_replay_error` | ✅ |
| `dlq_replay_worker` — CLI once/loop | ✅ |
| `POST /v1/events/dlq/replay-auto` | ✅ |
| EAS Update rollout gradual (`--rollout-percentage`) | ✅ |
| `GET /v1/mobile/eas/update/rollout/{plugin_id}` | ✅ |
| `scripts/eas-update-rollout.sh` | ✅ |
| Terraform remote state — `backend.hcl` export | ✅ |
| GitHub Actions `terraform-cdn.yml` (plan/apply) | ✅ |
| Versão `1.10.0-sprint20` | ✅ |

## DLQ Replay com Backoff

```bash
KAFKA_DLQ_REPLAY_ENABLED=true
KAFKA_DLQ_REPLAY_BACKOFF_BASE_SECONDS=30
KAFKA_DLQ_REPLAY_BACKOFF_MAX_SECONDS=3600
KAFKA_DLQ_REPLAY_MAX_ATTEMPTS=5

python -m app.workers.dlq_replay_worker --mode once
python -m app.workers.dlq_replay_worker --mode loop --interval 60

POST /v1/events/dlq/replay-auto?limit=20
POST /v1/events/dlq/{id}/replay?force=true
GET /v1/events/dlq/stats   # eligible_now
```

Backoff: `min(30 * 2^attempts, 3600)` segundos.

## EAS Update Rollout Gradual

```yaml
mobile:
  update:
    rollout_percentage: 50
    rollout_stages: [10, 25, 50, 100]
```

```bash
GET /v1/mobile/eas/update/rollout/sports?target_percentage=50
./scripts/eas-update-rollout.sh sports production 50 "Hotfix push"
```

## Terraform Remote State + CI Apply

```bash
make export-terraform-cdn
GET /v1/mobile/cdn/terraform/backend?environment=dev
./scripts/terraform-cdn.sh dev plan
./scripts/terraform-cdn.sh dev apply
```

GitHub Actions: `.github/workflows/terraform-cdn.yml`
- `workflow_dispatch`: plan ou apply
- Secrets: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`

Remote state: S3 `coreflow-terraform-state` + DynamoDB locks.

## Próximo: CF-21

- DLQ replay com reprocessamento handler-aware
- EAS Update canary por segmento de usuário
- Terraform multi-environment pipeline (dev → staging → prod)
