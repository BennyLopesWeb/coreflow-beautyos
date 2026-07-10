# Arquitetura CoreFlow

Ver também: [`BEAUTYOS_ARCHITECTURE.md`](../../BEAUTYOS_ARCHITECTURE.md) · [`COREFLOW_ANALYSIS.md`](../../COREFLOW_ANALYSIS.md)

## Stack Sprint 0

- **Backend:** Python 3.11, FastAPI, SQLAlchemy 2, Pydantic v2, SQLite (dev)  
- **Padrões:** DDD, Hexagonal, Event-Driven, Modular Monolith  
- **Plugins:** YAML manifest + PluginRegistry  

## Estrutura backend

```
backend/
├── app/
│   ├── core/
│   │   ├── plugin/       # PluginRegistry, PluginManifest
│   │   └── metamodel/    # CoreConcept enum
│   ├── modules/          # identity, booking (em progresso)
│   ├── shared/           # events, kernel
│   └── routers/          # legacy + /v1/plugins
└── plugins/
    └── beauty/
        └── manifest.yaml
```

## Fluxo Plugin First

1. Company possui `plugin_id`  
2. Startup carrega `backend/plugins/*/manifest.yaml`  
3. API expõe terminologia por tenant  
4. Frontend consome config — **Build Once. Configure Everywhere**  
