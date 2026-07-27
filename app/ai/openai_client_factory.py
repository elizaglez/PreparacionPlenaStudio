from __future__ import annotations

from app.ai.errors import AIProviderConfigurationError
from app.ai.openai_client_port import OpenAIClientPort


def create_openai_client(api_key: str) -> OpenAIClientPort:
    """Create an OpenAI client port from an explicitly supplied API key."""
    if not isinstance(api_key, str) or not api_key.strip():
        raise AIProviderConfigurationError(
            "La API key de OpenAI no puede estar vacía."
        )
    from app.ai.openai_client_adapter import OpenAIClientAdapter

    return OpenAIClientAdapter.from_api_key(api_key)
