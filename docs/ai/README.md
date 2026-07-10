# AI Platform

Visão alvo: abstrações provider-agnostic (OpenAI, Anthropic, Gemini, Azure, local).

| Estado | Local |
|--------|-------|
| Implementado (parcial) | `backend/app/modules/ai/` |
| SAB | `docs/08-AI-PLATFORM/` |
| BeautyAgent (migrar para plugin) | `backend/app/modules/ai/beauty_agent.py` |

## Componentes alvo (não implementados)

- AI Provider Registry
- Prompt Engine
- Memory / RAG
- Agent framework genérico
- Tools sobre domínio
- Vision / OCR / Speech adapters

**Regra:** IA nunca chamada diretamente nos routers — sempre via ports/application services.
