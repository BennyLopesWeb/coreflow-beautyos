"""
Interface abstrata para provedores LLM da AI Platform CoreFlow.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List


class LLMProvider(ABC):
    """
    Contrato para geração de insights/texto via LLM.

    Implementações: MockLLMProvider (rule-based), OpenAILLMProvider (HTTP).
    """

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """
        Identificador do provider (mock, openai).

        Returns:
            Nome curto do provider.
        """

    @abstractmethod
    def generate_insights(self, context: Dict[str, Any]) -> List[str]:
        """
        Gera insights textuais a partir de contexto estruturado.

        Args:
            context: Dict com company_id, pending_tasks, capabilities, etc.

        Returns:
            Lista de strings com sugestões para o operador.
        """

    @abstractmethod
    def is_available(self) -> bool:
        """
        Indica se o provider está configurado e operacional.

        Returns:
            True se pode ser usado.
        """
