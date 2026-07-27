from __future__ import annotations

from typing import NoReturn

from app.ai.provider import AIProvider


class OpenAIProviderNotImplementedError(RuntimeError):
    """Raised when the prepared provider is used before its implementation."""


class OpenAIProvider(AIProvider):
    """Prepared OpenAI adapter with no external integration yet."""

    @staticmethod
    def _not_implemented(operation: str) -> NoReturn:
        raise OpenAIProviderNotImplementedError(
            "El proveedor OpenAI todavía no implementa la operación "
            f"{operation!r}."
        )

    def generate_answer(
        self,
        question: str,
        context: list[str],
    ) -> str:
        self._not_implemented("generate_answer")

    def generate_application(self, answer: str) -> str:
        self._not_implemented("generate_application")

    def generate_summary(self, section_content: str) -> str:
        self._not_implemented("generate_summary")

    def generate_box_explanation(self, box_content: str) -> str:
        self._not_implemented("generate_box_explanation")

    def generate_heygen_transition(self, subtitle: str) -> str:
        self._not_implemented("generate_heygen_transition")
