from __future__ import annotations

from app.ai.config import AIProviderConfig
from app.ai.errors import AIProviderConfigurationError
from app.ai.fake_provider import FakeAIProvider
from app.ai.openai_provider import OpenAIProvider
from app.ai.provider import AIProvider


def create_provider(
    provider_name: str,
    config: AIProviderConfig,
) -> AIProvider:
    """Create a configured provider without invoking external services."""
    normalized_name = str(provider_name).strip().casefold()
    if normalized_name == "fake":
        return FakeAIProvider()
    if normalized_name == "openai":
        return OpenAIProvider(config)
    raise AIProviderConfigurationError(
        f"Proveedor de IA desconocido: {provider_name!r}."
    )
