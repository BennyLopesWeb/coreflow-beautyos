"""
Configurações da aplicação
Carrega variáveis de ambiente e define configurações padrão
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """
    Configurações da aplicação
    Valores podem ser definidos via variáveis de ambiente ou .env
    """
    
    # Database
    DATABASE_URL: str = "sqlite:///./trancapro.db"
    
    # App
    PLATFORM_NAME: str = "CoreFlow Platform"
    APP_NAME: str = "CoreFlow API"
    APP_VERSION: str = "2.13.0-r4-f10"

    # Feature flags — migração incremental (RFC-002) — default false (R1-F2)
    # R3-F2: booking.core.enabled default TRUE — path legado ACL/ReservationService
    # removido (ADR-027/ADR-033); manter flag apenas por compatibilidade de rollback.
    FEATURE_BOOKING_CORE_ENABLED: bool = True
    # R4-F2 introduziu FEATURE_BOOKING_LEGACY_PROJECTION_ENABLED como kill-switch do
    # dual-write outbound (project_*). R4-F3 (ADR-024 sunset / RFC-003 M7) removeu
    # definitivamente o código do dual-write — a flag não existe mais.
    # R4-F4 (ADR-024 sunset / RFC-003 M8 — hard sunset): novos paths de escrita
    # (FilaService.aprovar_fila, QueueEntryService.aprovar_com_horario) e
    # disponibilidade/fila-do-dia passam a usar ``core_bookings`` como SoT;
    # ``AgendamentoService.criar_agendamento`` agora falha (ver docstring do
    # método). ``agendamentos`` permanece somente leitura para histórico até
    # o DROP físico planejado em R4-F6.
    # R4-F5 (linkage FK + fechamento do gap operacional): ``queue_entries``/
    # ``fila`` ganham ``booking_id`` (FK nullable para ``core_bookings.id``);
    # checkin/iniciar/concluir passam a avançar ``CoreBooking.status`` para
    # entradas core-only. DROP físico de ``agendamentos``/``payments``/
    # ``schedules`` continua fora de escopo — adiado para R4-F6, condicionado
    # à migração de Payment/Schedule para o core.
    # R4-F6 (bridge Payment→booking_id + cutover disponibilidade core-only):
    # ``payments.agendamento_id`` passa a ser opcional e ``payments.booking_id``
    # (FK nullable ``core_bookings.id``) é adicionado; admin de pagamentos
    # legado (``/admin/pagamentos/{agendamento_id}/confirmar-sinal``) retorna
    # ``410 Gone``; ``aceitar_reagendamento`` deixa de escrever ``Schedule``.
    # R4-F7 (decouple físico das FKs restantes para ``agendamentos``):
    # ``schedules``/``satisfaction_surveys`` ganham ``agendamento_id``
    # nullable + ``booking_id`` (FK nullable ``core_bookings.id``); FK física
    # para ``agendamentos.id`` é removida de ``payments``, ``schedules``,
    # ``satisfaction_surveys``, ``fila``, ``queue_entries``, ``financeiro`` e
    # ``notification_logs`` (colunas ``agendamento_id`` permanecem como
    # ``Integer`` simples, sem constraint física — apenas leitura/histórico).
    # ``DisponibilidadeService`` passa a ler ocupação exclusivamente de
    # ``core_bookings``. Tabela ``agendamentos`` **não é removida** nesta
    # release — permanece necessária para fixtures/leitura histórica
    # (CF6/CF9/sync legado→core). DROP físico adiado explicitamente para
    # **R4-F8**.
    FEATURE_RESOURCE_ENGINE_ENABLED: bool = False
    FEATURE_AI_CORE_ENABLED: bool = False
    FEATURE_WORKFLOW_ENABLED: bool = False
    FEATURE_PLUGIN_ENGINE_ENABLED: bool = False
    FEATURE_LEGACY_TELEMETRY_ENABLED: bool = False

    # Enforcement warn em dev/staging quando mode=off (R1-F2)
    CORE_ENFORCEMENT_WARN_ENABLED: bool = True
    DEBUG: bool = False

    # Ambiente (development | staging | production)
    APP_ENV: str = "development"

    # Core enforcement — Fase B (off | warn | block)
    CORE_ENFORCEMENT_ENABLED: bool = False
    CORE_ENFORCEMENT_MODE: str = "off"

    # AI Platform LLM
    AI_LLM_ENABLED: bool = False
    AI_LLM_PROVIDER: str = "mock"
    AI_LLM_MODEL: str = "gpt-4o-mini"
    OPENAI_API_KEY: Optional[str] = None

    # Push mobile (CF-12/13)
    PUSH_NOTIFICATIONS_ENABLED: bool = True
    MOBILE_DEEP_LINK_SCHEME: str = "trancapro"
    MOBILE_UNIVERSAL_LINK_HOST: str = "app.coreflow.app"
    MOBILE_UNIVERSAL_LINK_PATH_PREFIX: str = "/*"
    MOBILE_IOS_APP_ID: str = "TEAMID12345.com.trancapro.app"
    MOBILE_IOS_BUNDLE_ID: str = "com.trancapro.app"
    MOBILE_ANDROID_PACKAGE: str = "com.trancapro.app"
    MOBILE_ANDROID_SHA256_FINGERPRINTS: str = (
        "14:6D:E9:83:C5:73:06:50:D8:EE:B9:95:2F:34:FC:64:16:A0:83:AE:E8:94:FF:4D:66:8F:0D:F6:1A:FE:E4:FF"
    )
    MOBILE_CDN_ENABLED: bool = True
    MOBILE_CDN_BASE_URL: str = "https://app.coreflow.app"
    MOBILE_WELL_KNOWN_CACHE_SECONDS: int = 86400
    EXPO_PUSH_ACCESS_TOKEN: Optional[str] = None
    EXPO_PUSH_LIVE: bool = False

    # Outbox dispatch (CF-13/14): sync | deferred | rabbitmq | kafka
    OUTBOX_DISPATCH_MODE: str = "sync"
    RABBITMQ_ENABLED: bool = False
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672/"
    KAFKA_ENABLED: bool = False
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_TOPIC: str = "coreflow.events"
    KAFKA_CONSUMER_GROUP: str = "coreflow-outbox-worker"
    KAFKA_DLQ_ENABLED: bool = True
    KAFKA_DLQ_TOPIC: str = "coreflow.events.dlq"
    KAFKA_DLQ_REPLAY_ENABLED: bool = True
    KAFKA_DLQ_REPLAY_BACKOFF_BASE_SECONDS: int = 30
    KAFKA_DLQ_REPLAY_BACKOFF_MAX_SECONDS: int = 3600
    KAFKA_DLQ_REPLAY_BATCH_SIZE: int = 20
    KAFKA_DLQ_REPLAY_MAX_ATTEMPTS: int = 5
    KAFKA_DLQ_REPLAY_MODE: str = "handler"

    KAFKA_SCHEMA_REGISTRY_ENABLED: bool = True
    KAFKA_SCHEMA_REGISTRY_MODE: str = "file"
    KAFKA_SCHEMA_REGISTRY_URL: str = "http://localhost:8081"
    KAFKA_SCHEMA_REGISTRY_USER: Optional[str] = None
    KAFKA_SCHEMA_REGISTRY_PASSWORD: Optional[str] = None
    KAFKA_SCHEMA_VALIDATE: bool = True
    KAFKA_SCHEMA_ENCODING: str = "json"
    MOBILE_CDN_PER_PLUGIN_PATH: bool = True
    MOBILE_EAS_WHITELABEL_ENABLED: bool = True
    MOBILE_EAS_SUBMIT_ENABLED: bool = True
    MOBILE_EAS_SUBMIT_APPLE_ID: str = "your-apple-id@email.com"
    MOBILE_EAS_SUBMIT_ASC_APP_ID: str = "0000000000"
    MOBILE_EAS_SUBMIT_APPLE_TEAM_ID: str = "TEAMID12345"
    MOBILE_EAS_SUBMIT_ANDROID_KEY_PATH: str = "./credentials/google-play-service-account.json"
    MOBILE_EAS_SUBMIT_ANDROID_TRACK: str = "internal"
    MOBILE_EAS_UPDATE_ENABLED: bool = True
    MOBILE_EAS_UPDATE_RUNTIME_VERSION: str = "1.0.0"
    MOBILE_EAS_UPDATE_ROLLOUT_ENABLED: bool = True
    MOBILE_EAS_UPDATE_DEFAULT_ROLLOUT_PCT: int = 100
    MOBILE_EAS_UPDATE_ROLLOUT_STAGES: str = "10,25,50,100"
    MOBILE_EAS_UPDATE_CANARY_ENABLED: bool = True
    MOBILE_EAS_UPDATE_CANARY_DEFAULT_PCT: int = 10
    MOBILE_EAS_UPDATE_CANARY_AUTO_PROMOTE: bool = True
    MOBILE_EAS_UPDATE_CANARY_HEALTH_LIVE: bool = False
    MOBILE_EAS_UPDATE_CANARY_HEALTH_MIN_SUCCESS_RATE: float = 0.99
    MOBILE_EAS_UPDATE_CANARY_HEALTH_MIN_SAMPLES: int = 10
    MOBILE_EAS_UPDATE_CANARY_AUTO_ROLLBACK: bool = True
    MOBILE_EAS_UPDATE_CANARY_ROLLBACK_THRESHOLD: float = 0.95
    MOBILE_EAS_UPDATE_CANARY_ROLLBACK_MIN_SAMPLES: int = 5

    # Prometheus metrics (CF-22)
    PROMETHEUS_ENABLED: bool = True
    PROMETHEUS_METRICS_PATH: str = "/metrics"

    # Grafana dashboards as code (CF-23)
    GRAFANA_DASHBOARDS_ENABLED: bool = True
    GRAFANA_PROMETHEUS_URL: str = "http://prometheus:9090"
    GRAFANA_PROMETHEUS_DATASOURCE: str = "Prometheus"

    # Alertmanager rules as code (CF-24)
    ALERTMANAGER_ENABLED: bool = True
    ALERTMANAGER_DLQ_PENDING_THRESHOLD: int = 10
    ALERTMANAGER_DLQ_ELIGIBLE_THRESHOLD: int = 5
    ALERTMANAGER_DLQ_FAILURE_RATE_THRESHOLD: float = 0.5
    ALERTMANAGER_DEFAULT_WEBHOOK_URL: str = "http://localhost:5001/alerts/default"
    ALERTMANAGER_CRITICAL_WEBHOOK_URL: str = "http://localhost:5001/alerts/critical"
    ALERTMANAGER_DLQ_WEBHOOK_URL: str = "http://localhost:5001/alerts/dlq"
    ALERTMANAGER_PAGERDUTY_ENABLED: bool = True
    ALERTMANAGER_PAGERDUTY_ROUTING_KEY: str = "pagerduty-routing-key-placeholder"
    ALERTMANAGER_OPSGENIE_ENABLED: bool = True
    ALERTMANAGER_OPSGENIE_API_KEY: str = "opsgenie-api-key-placeholder"

    MOBILE_EAS_UPDATE_CANARY_ROLLBACK_WORKER_ENABLED: bool = True
    MOBILE_EAS_UPDATE_CANARY_ROLLBACK_INTERVAL_SECONDS: int = 120
    MOBILE_EAS_UPDATE_CANARY_PERSIST_DB: bool = True

    # Terraform remote state (CF-20/21)
    TERRAFORM_STATE_BUCKET: str = "coreflow-terraform-state"
    TERRAFORM_STATE_REGION: str = "us-east-1"
    TERRAFORM_STATE_DYNAMODB_TABLE: str = "coreflow-terraform-locks"
    TERRAFORM_STATE_KEY_PREFIX: str = "cdn"
    TERRAFORM_PIPELINE_ENVIRONMENTS: str = "dev,staging,prod"
    TERRAFORM_DRIFT_ENABLED: bool = True
    TERRAFORM_DRIFT_LIVE: bool = False
    TERRAFORM_OPA_ENABLED: bool = True
    TERRAFORM_OPA_LIVE: bool = False
    TERRAFORM_SENTINEL_ENABLED: bool = True
    TERRAFORM_SENTINEL_COST_CENTER: str = "platform-coreflow"
    TERRAFORM_SENTINEL_OWNER: str = "platform-team"
    TERRAFORM_SENTINEL_MAX_ALIASES: int = 10
    TERRAFORM_SENTINEL_MAX_BEHAVIORS: int = 20
    TERRAFORM_SENTINEL_PROD_MIN_TTL: int = 300

    # Terraform Cloud policy sets (CF-25)
    TERRAFORM_CLOUD_ENABLED: bool = True
    TERRAFORM_CLOUD_ORGANIZATION: str = "coreflow-platform"
    TERRAFORM_CLOUD_POLICY_SET_NAME: str = "coreflow-cdn-policies"
    TERRAFORM_CLOUD_WORKSPACE_PREFIX: str = "coreflow-cdn-"
    TERRAFORM_CLOUD_API_TOKEN: Optional[str] = None

    # CDN S3/CloudFront sync (CF-17/18)
    CDN_S3_ENABLED: bool = False
    CDN_S3_BUCKET: str = "coreflow-cdn"
    CDN_S3_PREFIX: str = "cdn"
    CDN_S3_REGION: str = "us-east-1"
    CDN_S3_DRY_RUN: bool = True
    CDN_CLOUDFRONT_DISTRIBUTION_ID: Optional[str] = None
    CDN_CLOUDFRONT_ORIGIN_ID: str = "coreflow-cdn-s3"
    CDN_CLOUDFRONT_PRICE_CLASS: str = "PriceClass_100"
    CDN_CLOUDFRONT_RESPONSE_HEADERS_POLICY_ID: Optional[str] = None

    LEGACY_SUNSET_ENABLED: bool = True
    LEGACY_SUNSET_DATE: str = "Sat, 01 Jan 2028 00:00:00 GMT"

    # OpenTelemetry (opcional)
    OTEL_ENABLED: bool = False
    OTEL_SERVICE_NAME: str = "coreflow-api"
    
    # CORS
    CORS_ORIGINS: list[str] = ["*"]  # Em produção, especificar origens
    
    # Pagamento Pix (Mock)
    PIX_MOCK_ENABLED: bool = True
    
    # WhatsApp Webhook (Mock)
    WHATSAPP_WEBHOOK_ENABLED: bool = True
    WHATSAPP_API_URL: Optional[str] = None
    WHATSAPP_API_KEY: Optional[str] = None
    
    # Pix
    PIX_API_URL: Optional[str] = None
    PIX_API_KEY: Optional[str] = None
    PIX_MERCHANT_ID: Optional[str] = None
    
    # Google Calendar
    GOOGLE_CALENDAR_ENABLED: bool = False
    GOOGLE_CALENDAR_CREDENTIALS_FILE: Optional[str] = None
    GOOGLE_CALENDAR_TOKEN_FILE: Optional[str] = None
    GOOGLE_CALENDAR_ID: Optional[str] = None  # ID do calendário principal
    
    # JWT
    SECRET_KEY: str = "your-secret-key-change-in-production-use-env-var"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Instância global de configurações
settings = Settings()

