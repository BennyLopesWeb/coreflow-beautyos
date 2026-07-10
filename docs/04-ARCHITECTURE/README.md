# 04 — Architecture

Ver também: [`01-ARCHITECTURE/Architecture.md`](../01-ARCHITECTURE/Architecture.md) · [`COREFLOW_GAP_ANALYSIS.md`](../COREFLOW_GAP_ANALYSIS.md)

## Camadas

```
CoreFlow Platform
├── Core Engine (metamodelo, scheduling, events, identity)
├── Plugin Loader (manifest YAML)
└── Plugins (beauty, sports, clinic…)
```

## Padrões

- DDD + Hexagonal + Event-Driven + CQRS (parcial)
- Modular Monolith → microservices futuro
- Strangler Fig (legado + `/v1/*`)
- API First · Plugin First · AI First

## Observabilidade

- Logging: structlog
- Tracing: OpenTelemetry (`OTEL_ENABLED=true`) — CF-6 ✅
- CI: SQLite + MySQL — CF-6 ✅
