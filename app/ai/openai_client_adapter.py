from __future__ import annotations

from app.ai.openai_client_port import OpenAIClientPort


class OpenAIClientAdapter(OpenAIClientPort):
    """Adapt an injected text client to the OpenAI client port."""

    def __init__(self, client: OpenAIClientPort) -> None:
        self.client = client

    def generate_text(
        self,
        *,
        model: str,
        input_text: str,
        temperature: float | None,
        max_output_tokens: int | None,
        timeout_seconds: float,
    ) -> str:
        return self.client.generate_text(
            model=model,
            input_text=input_text,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            timeout_seconds=timeout_seconds,
        )
