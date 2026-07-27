from __future__ import annotations

from pathlib import Path

from app.ai.config import AIProviderConfig
from app.ai.errors import AIProviderConfigurationError
from app.ai.openai_client_factory import create_openai_client
from app.ai.openai_client_port import OpenAIClientPort
from app.ai.provider_factory import create_provider
from app.article_content_service import ArticleContentService


def create_article_content_service(
    provider_name: str,
    config: AIProviderConfig,
    *,
    openai_client: OpenAIClientPort | None = None,
    openai_api_key: str | None = None,
) -> ArticleContentService:
    """Compose the article content service from application settings."""
    if openai_client is not None and openai_api_key is not None:
        raise AIProviderConfigurationError(
            "No se puede proporcionar openai_client y openai_api_key "
            "al mismo tiempo."
        )

    client = openai_client
    normalized_name = str(provider_name).strip().casefold()
    if (
        normalized_name == "openai"
        and client is None
        and openai_api_key is not None
    ):
        client = create_openai_client(openai_api_key)
    provider = create_provider(
        provider_name,
        config,
        openai_client=client,
    )
    return ArticleContentService(provider)


def create_generate_article_content_use_case(
    provider_name: str,
    config: AIProviderConfig,
    project_root: str | Path,
    *,
    openai_client: OpenAIClientPort | None = None,
    openai_api_key: str | None = None,
):
    """Compose generation and project-local persistence."""
    from app.persistence.generated_article_repository import (
        JsonGeneratedArticleRepository,
    )
    from app.use_cases.generate_article_content import GenerateArticleContentUseCase

    service = create_article_content_service(
        provider_name,
        config,
        openai_client=openai_client,
        openai_api_key=openai_api_key,
    )
    repository = JsonGeneratedArticleRepository(project_root)
    return GenerateArticleContentUseCase(service, repository)
