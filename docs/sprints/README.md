# Sprints

Sprints de entrega técnica (CF-0 → CF-25 concluídos).

**Documentação ativa:** [`docs/04-SPRINTS/`](../04-SPRINTS/)

| Sprint | Versão | Foco |
|--------|--------|------|
| CF-0 … CF-25 | 0.1.0 → 1.15.0 | Ver `DOCUMENTACAO.md` §13 |
| R1-F1 | 1.16.0-r1-f1 | Governança: flags, event catalog, telemetria |
| R1-F2 | 1.17.0-r1-f2 | Platform health, ACL wiring, enforcement warn |
| R2-F0.5 | 1.18.5-r2-f0.5 | ACL wiring commands → ports |
| R2-F1 | 1.19.0-r2-f1 | Booking create domain — ✅ Accepted (tech) |
| R2-F1b | 1.19.1-r2-f1b | Idempotency + correlation — ✅ Accepted (tech) |
| R2-F2 | 1.20.0-r2-f2 | Approve/reject domain — ⏳ Ready (DoR) |
| R2-F6 | 2.0.0-beta.1 | Enforcement narrow booking |
| R3-F1 | 2.1.0-r3-f1 | Enforcement payments/fila + prod pilot — ✅ |
| R3-F2 | 2.2.0-r3-f2 | Remove booking write path legado (service de reservas) — ✅ |
| R3-F3 | 2.3.0-r3-f3 | Remove legacy write routers + fila→core — ✅ |
| R4-F1 | 2.4.0-r4-f1 | 410 Gone booking legado + catalog alias gone — ✅ |
| R4-F2 | 2.5.0-r4-f2 | Desligar dual-write outbound `project_*` por padrão (M7) — ✅ |
| R4-F3 | 2.6.0-r4-f3 | Remover código do dual-write outbound `project_*` (M7 completo) — ✅ |
| R4-F4 | 2.7.0-r4-f4 | Hard sunset — parar escritas novas em `agendamentos` (Option A, sem DROP); `core_bookings` SoT para disponibilidade/fila do dia (M8) — ✅ |
| R4-F5 | 2.8.0-r4-f5 | FK `booking_id` em `queue_entries`/`fila` + fechamento do gap operacional (M9) — ✅ |
| R4-F6 | 2.9.0-r4-f6 | Bridge `Payment`→`booking_id` + disponibilidade core-only + 410 admin legado (M10) — ✅ |
| R4-F7 | 2.10.0-r4-f7 | Decouple físico das últimas FKs para `agendamentos` (M11) — ✅ |
| R4-F8 | 2.11.0-r4-f8 | DROP físico de `agendamentos`; `Agendamento` deixa de ser model mapeado (M11+) — ✅ |
| R4-F9 | 2.12.0-r4-f9 | Financeiro em deposit core-only + 410 `/pagamentos/sinal*` — ✅ |
| R4-F10 | 2.13.0-r4-f10 | Pagamento final core-only + 410 `/payments/deposit\|final` — ✅ |
| R4-F11 | 2.14.0-r4-f11 | Reagendamento core-only (`POST /v1/bookings/{id}/reschedule`) — ✅ |
| R4-F12 | 2.15.0-r4-f12 | Transfer `payments`/`core_payments` no reschedule — ✅ |

Template: [templates/SprintTemplate.md](../templates/SprintTemplate.md)

Próximos: `completed`/`no_show`/`expired` (ADR-026); limpeza routers `pagamentos.py`/`payments.py`
