"""
Provider LLM OpenAI — opcional via httpx (fallback para mock se indisponível).
"""
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings
from app.core.logging_config import get_logger
from app.modules.ai.providers.base import LLMProvider
from app.modules.ai.providers.mock_provider import MockLLMProvider

logger = get_logger("openai_llm")


class OpenAILLMProvider(LLMProvider):
    """
    Provider OpenAI Chat Completions via HTTP.

    Requer ``OPENAI_API_KEY``; faz fallback transparente para MockLLMProvider
    se a chave estiver ausente ou a API falhar.

    Args:
        api_key: Chave OpenAI (default settings.OPENAI_API_KEY).
        model: Modelo chat (default settings.AI_LLM_MODEL).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self._api_key = api_key or settings.OPENAI_API_KEY
        self._model = model or settings.AI_LLM_MODEL
        self._fallback = MockLLMProvider()

    @property
    def provider_id(self) -> str:
        """
        Identificador do provider.

        Returns:
            ``openai`` se configurado, senão ``mock`` (fallback).
        """
        return "openai" if self.is_available() else "mock"

    def is_available(self) -> bool:
        """
        Verifica se OPENAI_API_KEY está definida.

        Returns:
            True se chave presente.
        """
        return bool(self._api_key)

    def generate_insights(self, context: Dict[str, Any]) -> List[str]:
        """
        Gera insights via OpenAI ou fallback mock.

        Args:
            context: Contexto estruturado do salão.

        Returns:
            Lista de insights textuais.
        """
        if not self.is_available():
            return self._fallback.generate_insights(context)

        pending_count = len(context.get("pending_tasks") or [])
        company_id = context.get("company_id", 0)
        capabilities = ", ".join(context.get("capabilities") or [])

        prompt = (
            f"Você é assistente de um salão de beleza (tenant {company_id}). "
            f"Capacidades IA: {capabilities}. "
            f"Tarefas pendentes: {pending_count}. "
            "Responda em português com até 3 bullets curtos e acionáveis."
        )

        try:
            response = httpx.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self._model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 200,
                    "temperature": 0.4,
                },
                timeout=15.0,
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            lines = [
                line.strip().lstrip("-•").strip()
                for line in content.split("\n")
                if line.strip()
            ]
            return lines[:3] if lines else self._fallback.generate_insights(context)
        except Exception as exc:
            logger.warning(f"OpenAI fallback mock: {exc}")
            return self._fallback.generate_insights(context)
