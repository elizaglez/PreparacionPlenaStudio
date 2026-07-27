from __future__ import annotations

from app.ai.config import AIProviderConfig
from app.ai.openai_client_factory import create_openai_client
from app.ai.openai_client_port import OpenAIClientPort
from app.ai.provider_factory import create_provider
from app.article_content_service import ArticleContentService


def create_article_content_service(
    provider_name: str,
    config: AIProviderConfig,
    *,
    openai_client: OpenAIClientPort | None = None,
) -> ArticleContentService:
    """Compose the article content service from application settings."""
    client = (
        create_openai_client(openai_client)
        if openai_client is not None
        else None
    )
    provider = create_provider(
        provider_name,
        config,
        openai_client=client,
    )
    return ArticleContentService(provider)
