from __future__ import annotations

from app.ai.openai_client_adapter import OpenAIClientAdapter
from app.ai.openai_client_port import OpenAIClientPort


def create_openai_client(client: OpenAIClientPort) -> OpenAIClientPort:
    """Create the OpenAI client port from an externally composed client."""
    return OpenAIClientAdapter(client)
