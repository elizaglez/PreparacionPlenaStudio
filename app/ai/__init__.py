from app.ai.provider import AIProvider


_LEGACY_EXPORTS = {
    "AIConfigurationError",
    "AIResponseError",
    "OpenAIEditor",
}


def __getattr__(name: str):
    """Load the OpenAI implementation only when explicitly requested."""
    if name not in _LEGACY_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    from app.ai import openai_client

    return getattr(openai_client, name)


__all__ = ["AIProvider"]
