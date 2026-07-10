## Summary

<!-- Descreva o que mudou e por quê -->

## Sprint / Release

- [ ] R2-F2 — approve/reject
- [ ] R2-F2b — cancel
- [ ] R2-F3 — resource engine
- [ ] Outro: ___

## Checklist

- [ ] Escopo limitado ao sprint doc
- [ ] `pytest -o addopts=` verde
- [ ] Paridade aplicável PASS
- [ ] Sprint doc / Decision Log atualizados
- [ ] Sem secrets (.env, credentials)

## Test plan

```bash
cd backend
python -m pytest -o addopts= -q
```

## Rollback

```bash
export FEATURE_BOOKING_CORE_ENABLED=false
export FEATURE_RESOURCE_ENGINE_ENABLED=false
```

## Referências

- Sprint: `docs/sprints/`
- Gate: `docs/reviews/`
