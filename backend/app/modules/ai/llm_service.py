"""
LLM Service — factory de providers AI Platform CoreFlow.
"""
from typing import Optional

from app.core.config import settings
from app.modules.ai.providers.base import LLMProvider
from app.modules.ai.providers.mock_provider import MockLLMProvider
from app.modules.ai.providers.openai_provider import OpenAILLMProvider


class LLMService:
    """
    Resolve provider LLM conforme configuração da plataforma.

    ``AI_LLM_ENABLED=false`` → sempre MockLLMProvider.
    ``AI_LLM_PROVIDER=openai`` → OpenAILLMProvider (fallback mock).
    """

    _instance: Optional[LLMProvider] = None

    @classmethod
    def get_provider(cls) -> LLMProvider:
        """
        Retorna provider singleton conforme settings.

        Returns:
            Instância LLMProvider operacional.
        """
        if cls._instance is not None:
            return cls._instance

        if not settings.AI_LLM_ENABLED:
            cls._instance = MockLLMProvider()
            return cls._instance

        provider_name = (settings.AI_LLM_PROVIDER or "mock").lower()
        if provider_name == "openai":
            openai = OpenAILLMProvider()
            cls._instance = openai if openai.is_available() else MockLLMProvider()
        else:
            cls._instance = MockLLMProvider()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """
        Limpa cache singleton (útil em testes).

        Returns:
            None
        """
        cls._instance = None
