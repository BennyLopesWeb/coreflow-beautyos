# Decision log — Assunção técnica

**Referência de código:** `b632ea8`  
**Data:** 2026-07-28  

Registra apenas decisões com status claro. Hipóteses → `unknowns-and-decisions.md`.

| Data | Decisão | Contexto | Alternativas | Decisor | Impacto | Status |
|------|---------|----------|--------------|---------|---------|--------|
| 2026-07-28 | Assunção segue Prompt001 (FASE 1→3) sem alterar código até diagnóstico | Transição de liderança | Alterar código durante diagnóstico | Liderança técnica | Processo | Decidida |
| 2026-07-28 | Corrigir timezone no create booking (`as_naive_utc`) | Smoke FASE 3: TypeError aware vs naive | Rejeitar ISO com Z; migrar stack inteira para aware | Assunção técnica | Booking / DX | Decidida (`b632ea8`) |
| 2026-07-28 | Commit B-TZ isolado (4 arquivos), sem misturar docs/infra/FE | Working tree suja | Commit monólito | Assunção técnica | Git hygiene | Decidida |
| 2026-07-28 | Não iniciar Wave 3 OPS sem prioridade explícita do PO | Prompt002 continuidade | Iniciar flatten platform/obs/ai/mobile | Prompt002 / liderança | Escopo | Decidida |
| 2026-07-28 | Não mover payments write para hexagonal nesta fase | Divergência policy×código | Refactor payments agora | Prompt002 | Escopo / risco | Decidida |
| 2026-07-28 | Não fazer push automático do `b632ea8` | Controlo de publicação | Push imediato | Prompt comandos | Release | Decidida (aguardar OK) |
| 2026-07-28 | Criar docs oficiais FASE 8 em `docs/assumption/` (4 arquivos) | Prompt autorização documentação | Adiar documentação | Prompt docs | Conhecimento | Decidida (arquivos criados; commit docs pendente) |
| — | Hospedagem alvo da API | Deploy não no repo | VM / ECS / K8s / PaaS / outro | — | Infra | Aberta |
| — | Hardening SECRET_KEY + CORS em código | Defaults inseguros | Só documentação | — | Segurança | Aberta |
| — | Estratégia de limpeza FE legado | Rotas 410 / fila | Big-bang vs incremental | — | Produto | Aberta |
