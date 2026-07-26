from __future__ import annotations

from app.ai.provider import AIProvider


class FakeAIProvider(AIProvider):
    """Deterministic provider used by tests without external services."""

    def generate_answer(
        self,
        question: str,
        context: list[str],
    ) -> str:
        return "Respuesta simulada para prueba"

    def generate_application(self, answer: str) -> str:
        return "Aplicación simulada para prueba"

    def generate_summary(self, section_content: str) -> str:
        return "Resumen simulado para prueba"

    def generate_heygen_transition(self, subtitle: str) -> str:
        return "Transición HeyGen simulada para prueba"
