from __future__ import annotations

from app.ai.config import AIProviderConfig
from app.ai.errors import AIProviderConfigurationError
from app.ai.openai_client_port import OpenAIClientPort
from app.ai.provider import AIProvider


class OpenAIProvider(AIProvider):
    """Prepared OpenAI adapter with no external integration yet."""

    def __init__(
        self,
        config: AIProviderConfig,
        client: OpenAIClientPort | None = None,
    ) -> None:
        self.config = config
        self.client = client

    def _generate_text(self, input_text: str) -> str:
        if self.client is None:
            raise AIProviderConfigurationError(
                "OpenAIProvider necesita un cliente compatible con "
                "OpenAIClientPort."
            )
        return self.client.generate_text(
            model=self.config.model,
            input_text=input_text,
            temperature=self.config.temperature,
            max_output_tokens=self.config.max_output_tokens,
            timeout_seconds=self.config.timeout_seconds,
        )

    def generate_answer(
        self,
        question: str,
        context: list[str],
    ) -> str:
        return self._generate_text("\n\n".join([question, *context]))

    def generate_application(self, answer: str) -> str:
        return self._generate_text(answer)

    def generate_summary(self, section_content: str) -> str:
        return self._generate_text(section_content)

    def generate_box_explanation(self, box_content: str) -> str:
        return self._generate_text(box_content)

    def generate_heygen_transition(self, subtitle: str) -> str:
        return self._generate_text(subtitle)
