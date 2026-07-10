# CoreFlow — Developer Experience (DX)

**Documento:** `docs/DeveloperExperience.md`  
**Versão:** 1.0 · **Data:** 2026-07-09  
**Status:** Estratégico — CLI, produtividade, Developer Platform  
**Release alvo:** R6 — design completo agora

---

## Visão

**Developer Experience** é a capacidade da plataforma de maximizar produtividade de quem constrói sobre CoreFlow — internos, parceiros ISV e community contributors.

Meta: **novo plugin MVP em <1 dia** com CLI + templates + validação automática.

---

## CLI oficial: `coreflow`

### Instalação (futuro)

```bash
npm install -g @coreflow/cli
# ou
pip install coreflow-cli
```

### Comandos

| Comando | Descrição | Release |
|---------|-----------|---------|
| `coreflow new plugin <id>` | Scaffold plugin completo | R6 |
| `coreflow new workflow <name>` | YAML workflow + test | R4 |
| `coreflow new aggregate <name>` | Domain aggregate stub (ADR required) | R6 |
| `coreflow new adapter <name>` | ACL/Integration adapter | R4 |
| `coreflow new event <type>` | Event + Avro schema + catalog entry | R4 |
| `coreflow new port <name>` | Protocol stub | R6 |
| `coreflow doctor` | Health check projeto local | R3 |
| `coreflow validate` | Manifest, events, fitness functions | R3 |
| `coreflow migrate` | Alembic wrapper + safety checks | R3 |
| `coreflow deploy plugin` | Deploy to staging/prod | R6 |
| `coreflow scaffold <template>` | Template from marketplace | R6 |
| `coreflow test parity` | Run paridade legado vs v1 | R2 |
| `coreflow test fitness` | Architecture fitness functions | R3 |
| `coreflow login` | Auth dev portal | R6 |
| `coreflow marketplace publish` | Publish asset | R6 |

---

## `coreflow new plugin` — output esperado

```
backend/plugins/sports/
├── manifest.yaml
backend/app/plugins/sports/
├── hooks/
│   └── __init__.py
├── agents/
├── tests/
│   └── test_manifest.py
frontend/plugins/sports/          # optional stub
packages/coreflow-sdk/plugins/sports/  # types extension
```

Prompts interativos:

- Terminology wizard
- Features checklist
- Resource types
- Mobile whitelabel yes/no

---

## `coreflow doctor`

Validações locais:

```
✓ Python 3.11+
✓ Node 18+
✓ pytest available
✓ APP_VERSION matches git tag
✓ Feature flags documented
✓ No Constitution violations (import-linter)
✓ Event catalog synced
✓ Plugin manifests valid YAML schema
⚠ Legacy coupling: booking/commands → ReservationService (R2 pending)
```

Exit code non-zero on errors — CI friendly.

---

## `coreflow validate`

| Check | Tool |
|-------|------|
| Manifest schema | JSON Schema |
| Event in catalog | event_catalog.py sync |
| OpenAPI breaking | oasdiff |
| Fitness functions | `scripts/architecture_fitness.py` |
| Plugin hooks importable | dynamic import test |
| Terminology complete | manifest validator |

---

## Produtividade — métricas DX

| Métrica | Baseline | Target R6 |
|---------|----------|-----------|
| Time to first plugin | ~2 weeks | <1 day |
| Time to add event | ~4 hours | <30 min |
| Onboarding doc → first PR | ~1 week | <2 days |
| CLI command success rate | — | >95% |
| Developer NPS | — | >50 |

---

## Developer Portal (web)

| Feature | Release |
|---------|---------|
| Docs (GitBook/Docusaurus) | R3 |
| API Explorer (OpenAPI) | R6 |
| Sandbox tenant auto-provision | R6 |
| CLI auth + API keys | R6 |
| Tutorial paths ("Build Sports Plugin") | R6 |
| Status page | R3 |
| Changelog / migration guides | R2+ per release |

URL: `developers.coreflow.app`

---

## SDK ecosystem

| Package | Status | DX note |
|---------|--------|---------|
| `@coreflow/sdk` | ✅ | Auto-gen from OpenAPI R6 |
| `@coreflow/cli` | 🔜 R6 | Node-based |
| `coreflow-cli` (Python) | 🔜 R6 | Backend plugin dev |
| `@coreflow/plugin-sdk` | 🔜 R6 | Hook types, test utils |
| `@coreflow/ui-components` | 🔜 R5 | LCP component library |

---

## Local development

### Makefile targets (expandir)

```makefile
make dev          # docker compose up
make test         # pytest
make fitness      # architecture fitness functions
make validate     # coreflow validate
make openapi      # export openapi.json
```

### Dev containers

`.devcontainer/` — VS Code / Cursor one-click (R4).

### Sandbox tenant

CLI `coreflow sandbox create` — isolated tenant + sample data (R6).

---

## CI/CD for plugin developers

GitHub Action template (R6):

```yaml
- uses: coreflow/validate-action@v1
- uses: coreflow/certify-action@v1  # optional pre-publish
- run: coreflow marketplace publish --dry-run
```

---

## Documentation as code

- OpenAPI spec exported each release
- Event catalog = source of truth
- ADR/RFC templates in `docs/templates/`
- Changelog auto from conventional commits

---

## Roadmap DX

| Release | Entrega |
|---------|---------|
| R2 | `coreflow test parity` concept, OpenAPI export |
| R3 | `doctor`, `validate`, `migrate` MVP scripts |
| R4 | `new event`, `new workflow`, `new adapter` |
| R5 | Template install from marketplace |
| R6 | Full CLI, portal web, SDK codegen, CI actions |
| R7 | i18n CLI, regional sandbox |

---

## Referências

- `docs/DeveloperPortal.md` — how-to guides
- `docs/EngineeringHandbook.md` — standards
- `docs/PluginCertification.md` — publish pipeline
- `docs/ArchitectureFitnessFunctions.md` — validate in CI
- `packages/coreflow-sdk/`
