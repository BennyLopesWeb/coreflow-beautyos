# CoreFlow Platform

**Build Once. Configure Everywhere.**

Framework SaaS modular (API First · AI First · Event-Driven · Hexagonal · Plugin First).

**BeautyOS** é o primeiro produto — plugin `beauty` sobre o CoreFlow Engine.

**Release atual:** `2.7.0-r4-f4` · R4-F4 Implemented (tech) · próximo: R4-F5+ (avaliar drop físico de `agendamentos` legado)

---

## Documentação

| Recurso | Link |
|---------|------|
| **Docs SAB** | [`docs/README.md`](docs/README.md) |
| **Sprint R2-F2b** | [`docs/sprints/R2-F2b.md`](docs/sprints/R2-F2b.md) |
| **Sprint R2-F3 (próxima)** | [`docs/sprints/R2-F3.md`](docs/sprints/R2-F3.md) |
| **PR R2-F2b** | [`docs/pull-requests/R2-F2b-PR.md`](docs/pull-requests/R2-F2b-PR.md) |
| **Análise estratégica** | [`COREFLOW_ANALYSIS.md`](COREFLOW_ANALYSIS.md) |
| **Sprint 0** | [`docs/04-SPRINTS/Sprint00.md`](docs/04-SPRINTS/Sprint00.md) |
| **ADR Metamodelo** | [`docs/06-ADR/ADR001-metamodel.md`](docs/06-ADR/ADR001-metamodel.md) |
| **Regras de negócio (beauty)** | [`DOCUMENTACAO.md`](DOCUMENTACAO.md) |

---

## Quick start

```bash
make install
make migrate
make test
make run
```

- API: http://localhost:8000/docs  
- Plugins: http://localhost:8000/v1/plugins  
- Config tenant: http://localhost:8000/v1/plugins/config/by-company/salao-demo  

---

## Estrutura

```
├── docs/              # Software Architecture Blueprint (SAB)
├── backend/
│   ├── app/           # CoreFlow API
│   └── plugins/
│       └── beauty/    # BeautyOS manifest
├── frontend/          # Expo (plugin beauty — temporário)
├── docker-compose.yml
└── Makefile
```

---

## Plugins registrados

| plugin_id | Produto | Status |
|-----------|---------|--------|
| `beauty` | BeautyOS | ✅ Ativo |

---

*CoreFlow Platform · Benigno Fernandes Lopes · Release 2 — F2b*
