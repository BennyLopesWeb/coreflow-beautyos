# 08 — AI Platform

Módulo IA da CoreFlow — providers plugáveis, não apenas OpenAI wrapper.

| Capacidade | Status |
|------------|--------|
| LLM Providers (mock, OpenAI) | ✅ CF-8 |
| BeautyAgent + manifest ai_capabilities | ✅ CF-7 |
| Agents (CRM, fila, pagamentos) | ⚠️ `AgenteService` rule-based |
| Chat / Vision / OCR | 🔜 CF-9+ |
| RAG / Knowledge Base | 🔜 |
| Business Automation (workflows) | ✅ CF-8 WorkflowEngine |

## Arquitetura CF-8

```
BeautyAgent → LLMService → MockLLMProvider | OpenAILLMProvider
                ↑
         AI_LLM_ENABLED / AI_LLM_PROVIDER / OPENAI_API_KEY
```

Eventos de domínio → WorkflowEngine (YAML) → ações (notify_admin, log…).

Código: `backend/app/modules/ai/`
