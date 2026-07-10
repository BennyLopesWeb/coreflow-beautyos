# 00 — Executive Summary

**CoreFlow Platform** · Build Once. Configure Everywhere.

## O que é

Framework SaaS para aplicações orientadas a serviços. BeautyOS (trancista) é o **plugin piloto #1**, não o produto final.

## Veredicto (Jul 2026)

| Métrica | Valor |
|---------|-------|
| Reaproveitamento backend | ~70% |
| Sprints concluídos | CF-0 → CF-4 (em progresso) |
| Testes automatizados | 50+ |
| Meta Model ORM | 7 tabelas `core_*` |
| Legado coexistindo | Strangler Fig + Sunset RFC 8594 |

## Diferencial

**Core conhece apenas conceitos universais** (Resource, Booking, Worker…). Domínios (Beauty, Sports, Clinic) **configuram** via plugins — 90% do código igual entre verticais.

## Documentos-chave

- [`COREFLOW_GAP_ANALYSIS.md`](../COREFLOW_GAP_ANALYSIS.md) — gap vs visão final
- [`07-META-MODEL/README.md`](../07-META-MODEL/README.md) — coração da plataforma
- [`17-SPRINTS/Sprint00.md`](../04-SPRINTS/Sprint00.md) — entregas por sprint

## Próximo marco

CF-4: Scheduling Engine + Resource Engine no código · CF-5: `core_customers`, Outbox, AI proto.
