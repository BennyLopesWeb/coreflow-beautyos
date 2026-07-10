"""
Provider LLM mock — rule-based, sem dependência externa (default dev/test).
"""
from typing import Any, Dict, List

from app.modules.ai.providers.base import LLMProvider


class MockLLMProvider(LLMProvider):
    """
    Provider rule-based que simula respostas de LLM para protótipo CF-8.

    Usado quando ``AI_LLM_PROVIDER=mock`` ou quando OpenAI não está configurado.
    """

    @property
    def provider_id(self) -> str:
        """
        Identificador do provider.

        Returns:
            ``mock``.
        """
        return "mock"

    def is_available(self) -> bool:
        """
        Mock sempre disponível.

        Returns:
            True.
        """
        return True

    def generate_insights(self, context: Dict[str, Any]) -> List[str]:
        """
        Gera insights com base em contadores de tarefas pendentes.

        Args:
            context: Deve conter pending_tasks (list), company_id, capabilities.

        Returns:
            Lista de sugestões textuais.
        """
        pending = context.get("pending_tasks") or []
        company_id = context.get("company_id", 0)
        capabilities = context.get("capabilities") or []
        insights: List[str] = []

        waitlist_count = sum(
            1 for t in pending if getattr(getattr(t, "tipo", None), "value", "") == "notificar_fila"
        )
        payment_count = sum(
            1
            for t in pending
            if getattr(getattr(t, "tipo", None), "value", "") == "lembrete_pagamento"
        )

        if "waitlist_notify" in capabilities and waitlist_count:
            insights.append(f"{waitlist_count} cliente(s) na fila aguardam contato.")
        if "payment_reminder" in capabilities and payment_count:
            insights.append(f"{payment_count} reserva(s) com sinal pendente.")
        if not insights:
            insights.append(
                f"Salão #{company_id} — {len(pending)} tarefa(s) pendente(s) "
                f"(provider=mock)."
            )
        return insights
