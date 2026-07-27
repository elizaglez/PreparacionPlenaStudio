class AIProviderError(RuntimeError):
    """Base error raised by AI providers."""


class AIProviderTemporaryError(AIProviderError):
    """Recoverable provider failure that may succeed when retried."""


class AIProviderPermanentError(AIProviderError):
    """Non-recoverable provider failure that should not be retried unchanged."""


class AIProviderConfigurationError(AIProviderPermanentError):
    """Invalid or incomplete provider configuration."""


class AIProviderResponseError(AIProviderPermanentError):
    """Invalid response returned by a provider."""
