from __future__ import annotations

from dataclasses import dataclass

from app.ai.errors import AIProviderConfigurationError


@dataclass(frozen=True)
class AIProviderConfig:
    """Provider-agnostic generation settings without credentials."""

    model: str
    timeout_seconds: float
    temperature: float | None = None
    max_output_tokens: int | None = 1024

    def __post_init__(self) -> None:
        if not isinstance(self.model, str) or not self.model.strip():
            raise AIProviderConfigurationError("El modelo no puede estar vacío.")
        if (
            isinstance(self.timeout_seconds, bool)
            or not isinstance(self.timeout_seconds, (int, float))
            or self.timeout_seconds <= 0
        ):
            raise AIProviderConfigurationError(
                "El tiempo de espera debe ser positivo."
            )
        if self.max_output_tokens is not None and (
            isinstance(self.max_output_tokens, bool)
            or not isinstance(self.max_output_tokens, int)
            or self.max_output_tokens <= 0
        ):
            raise AIProviderConfigurationError(
                "El límite de tokens de salida debe ser positivo."
            )
        if self.temperature is not None and (
            isinstance(self.temperature, bool)
            or not isinstance(self.temperature, (int, float))
            or not 0.0 <= self.temperature <= 2.0
        ):
            raise AIProviderConfigurationError(
                "La temperatura debe estar entre 0.0 y 2.0."
            )
