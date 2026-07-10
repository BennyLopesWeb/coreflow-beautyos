# Plugins — CoreFlow Platform

Framework de plugins verticais (BeautyOS, SportsOS, ClinicOS, …).

| Recurso | Local |
|---------|-------|
| Manifests | `backend/plugins/*/manifest.yaml` |
| Registry | `backend/app/core/plugin/registry.py` |
| API | `GET /v1/plugins` |
| SAB | `docs/06-PLUGIN-FRAMEWORK/`, `docs/03-PLUGINS/` |
| RFC plugin engine | `docs/rfc/` (planejado RFC-003) |

**Regra:** o Core nunca conhece terminologia vertical (Tranca, Quadra, Consultório). Plugins especializam via manifest.
