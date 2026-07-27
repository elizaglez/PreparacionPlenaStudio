from __future__ import annotations

from typing import Any

from app.ai.openai_client_port import OpenAIClientPort


class FakeOpenAIClient(OpenAIClientPort):
    """Deterministic OpenAI client port implementation for tests."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def generate_text(
        self,
        *,
        model: str,
        input_text: str,
        temperature: float | None,
        max_output_tokens: int | None,
        timeout_seconds: float,
    ) -> str:
        self.calls.append(
            {
                "model": model,
                "input_text": input_text,
                "temperature": temperature,
                "max_output_tokens": max_output_tokens,
                "timeout_seconds": timeout_seconds,
            }
        )
        return "Fake AI response"
