from __future__ import annotations
from abc import ABC, abstractmethod


class ProviderError(RuntimeError):
    """Sanitized provider error, without request bodies or credentials."""


class LLMProvider(ABC):
    name = 'base'
    model = ''

    @abstractmethod
    def generate(self, prompt: str, context: dict | None = None, language: str = 'en') -> dict:
        """Return sentence selections from the supplied grounded context."""
