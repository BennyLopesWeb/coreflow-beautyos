# CoreFlow Platform — Makefile
# Build Once. Configure Everywhere.

.PHONY: help install test fitness run migrate alembic-upgrade docker-up docker-down docker-mysql-up docker-mysql-down docker-rabbitmq-up docker-rabbitmq-down docker-kafka-up docker-kafka-down outbox-worker lint

help:
	@echo "CoreFlow Platform — comandos disponíveis:"
	@echo "  make install          Instala dependências do backend"
	@echo "  make test             Executa testes"
	@echo "  make fitness          Gate Architecture Fitness F5 (ERROR)"
	@echo "  make run              Inicia API (porta 8000)"
	@echo "  make migrate          Bootstrap SQLite + sync metamodelo"
	@echo "  make alembic-upgrade  Aplica migrações Alembic (head)"
	@echo "  make docker-up        Sobe API com SQLite"
	@echo "  make docker-mysql-up  Sobe API + MySQL 8"
	@echo "  make docker-down      Para containers"
	@echo "  make docker-mysql-down Para containers MySQL"
	@echo "  make docker-rabbitmq-up  Sobe API + RabbitMQ + outbox worker"
	@echo "  make docker-rabbitmq-down Para stack RabbitMQ"
	@echo "  make docker-kafka-up     Sobe API + Kafka + outbox worker"
	@echo "  make docker-kafka-down   Para stack Kafka"
	@echo "  make outbox-worker     Worker outbox (poll once)"

install:
	cd backend && pip install -r requirements.txt

test:
	cd backend && python -m pytest tests/ -q -o addopts=""

fitness:
	python scripts/architecture_fitness_check.py --phase f5

run:
	cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

migrate:
	cd backend && python -c "from app.db.init_db import init_db; init_db()"

alembic-upgrade:
	cd backend && alembic upgrade head

docker-up:
	docker compose up -d --build

docker-mysql-up:
	docker compose -f docker-compose.yml -f docker-compose.mysql.yml up -d --build

docker-down:
	docker compose down

docker-mysql-down:
	docker compose -f docker-compose.yml -f docker-compose.mysql.yml down

docker-rabbitmq-up:
	docker compose -f docker-compose.yml -f docker-compose.rabbitmq.yml up -d --build

docker-rabbitmq-down:
	docker compose -f docker-compose.yml -f docker-compose.rabbitmq.yml down

docker-kafka-up:
	docker compose -f docker-compose.yml -f docker-compose.kafka.yml up -d --build

docker-kafka-down:
	docker compose -f docker-compose.yml -f docker-compose.kafka.yml down

export-well-known:
	cd backend && python -c "from app.modules.mobile.application.well_known_export_service import WellKnownExportService; print(WellKnownExportService().export_to_disk())"

export-well-known-all:
	cd backend && python -c "from app.core.plugin.registry import plugin_registry; from app.modules.mobile.application.plugin_cdn_service import PluginCdnService; plugin_registry.load_all(); print(PluginCdnService().export_all_plugins())"

docker-schema-registry-up:
	docker compose -f docker-compose.yml -f docker-compose.kafka.yml -f docker-compose.schema-registry.yml up -d --build

docker-schema-registry-down:
	docker compose -f docker-compose.yml -f docker-compose.kafka.yml -f docker-compose.schema-registry.yml down

docker-cdn-up:
	docker compose -f docker-compose.yml -f docker-compose.cdn.yml up -d --build

docker-cdn-down:
	docker compose -f docker-compose.yml -f docker-compose.cdn.yml down

cdn-sync-s3:
	chmod +x scripts/cdn-sync-s3.sh && ./scripts/cdn-sync-s3.sh true

cdn-sync-s3-live:
	chmod +x scripts/cdn-sync-s3.sh && CDN_S3_ENABLED=true CDN_S3_DRY_RUN=false ./scripts/cdn-sync-s3.sh false

eas-generate:
	cd backend && python -c "from app.core.plugin.registry import plugin_registry; from app.modules.mobile.application.eas_whitelabel_service import EasWhitelabelService; plugin_registry.load_all(); print(EasWhitelabelService().generate_plugins_file())"

eas-submit-generate:
	cd backend && python -c "from app.core.plugin.registry import plugin_registry; from app.modules.mobile.application.eas_submit_service import EasSubmitService; plugin_registry.load_all(); print(EasSubmitService().generate_submit_file())"

export-cloudfront-behaviors:
	cd backend && python -c "from app.core.plugin.registry import plugin_registry; from app.modules.mobile.application.cloudfront_behaviors_service import CloudFrontBehaviorsService; plugin_registry.load_all(); print(CloudFrontBehaviorsService().export_to_disk())"

export-terraform-cdn:
	cd backend && python -c "from app.core.plugin.registry import plugin_registry; from app.modules.mobile.application.terraform_export_service import TerraformExportService; plugin_registry.load_all(); print(TerraformExportService().export_tfvars('dev'))"

eas-update-generate:
	cd backend && python -c "from app.core.plugin.registry import plugin_registry; from app.modules.mobile.application.eas_update_service import EasUpdateService; plugin_registry.load_all(); print(EasUpdateService().generate_update_file())"

dlq-replay-once:
	cd backend && python -m app.workers.dlq_replay_worker --mode once

dlq-replay-loop:
	cd backend && python -m app.workers.dlq_replay_worker --mode loop --interval 60

terraform-cdn-plan:
	chmod +x scripts/terraform-cdn.sh && ./scripts/terraform-cdn.sh dev plan

terraform-pipeline-export:
	chmod +x scripts/terraform-pipeline.sh && ./scripts/terraform-pipeline.sh export

terraform-pipeline-plan:
	chmod +x scripts/terraform-pipeline.sh && ./scripts/terraform-pipeline.sh plan-all

terraform-drift-check:
	chmod +x scripts/terraform-drift.sh && ./scripts/terraform-drift.sh all config

grafana-export:
	chmod +x scripts/grafana-export.sh && ./scripts/grafana-export.sh

alertmanager-export:
	chmod +x scripts/alertmanager-export.sh && ./scripts/alertmanager-export.sh

terraform-policy-check:
	chmod +x scripts/terraform-policy.sh && ./scripts/terraform-policy.sh all

terraform-sentinel-check:
	chmod +x scripts/terraform-sentinel.sh && ./scripts/terraform-sentinel.sh all

terraform-cloud-policy-export:
	chmod +x scripts/terraform-cloud-policy.sh && ./scripts/terraform-cloud-policy.sh

canary-rollback-once:
	cd backend && python -m app.workers.canary_rollback_worker --mode once

canary-rollback-loop:
	cd backend && python -m app.workers.canary_rollback_worker --mode loop --interval 120

outbox-worker:
	cd backend && python -m app.workers.outbox_worker --mode once

lint:
	cd backend && python -m compileall app
