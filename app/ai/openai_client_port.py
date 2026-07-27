from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class OpenAIClientPort(Protocol):
    def generate_text(
        self,
        *,
        model: str,
        input_text: str,
        temperature: float | None,
        max_output_tokens: int | None,
        timeout_seconds: float,
    ) -> str:
        ...
