# ADR-002 — BeautyOS como Plugin Oficial #1

| | |
|---|---|
| **Status** | Aceito |
| **Data** | 2026-07-09 |

## Contexto

Todo o código existente (reservas, fila, sinal, catálogo trancista) representa meses de regras de negócio validadas.

## Decisão

1. **Não reescrever** — evoluir via Strangler Fig  
2. BeautyOS = produto comercial do plugin `beauty`  
3. Empresa demo (`salao-demo`) usa `plugin_id: beauty`  
4. APIs legadas (`/trancas`, `/reservations`) permanecem; APIs genéricas nascem em paralelo  

## Manifest

`backend/plugins/beauty/manifest.yaml`

## Features declaradas

- `deposit_payment` — sinal 30%  
- `waitlist` — fila de espera  
- `operational_queue` — fila do dia  
- `approval_workflow` — admin aprova reserva  
- `ai_vision` — roadmap  

## Consequências

- Frontend pode chamar `GET /v1/plugins/config/by-company/{slug}` para rótulos dinâmicos  
- Branding UI: BeautyOS; plataforma: CoreFlow  
