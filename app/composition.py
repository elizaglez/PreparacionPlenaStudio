from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from pathlib import Path

from app.ai.config import AIProviderConfig
from app.ai.errors import AIProviderConfigurationError
from app.ai.openai_client_factory import create_openai_client
from app.ai.openai_client_port import OpenAIClientPort
from app.ai.provider_factory import create_provider
from app.article_content_service import ArticleContentService
from app.generation.article_generation_plan import build_article_generation_plan
from app.models import Project
from app.security.secret_loader import SecretLoader
from app.storage import load_settings


OPENAI_DEFAULT_TIMEOUT_SECONDS = 600.0


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
    ):
        if openai_api_key is None:
            openai_api_key = SecretLoader().get_secret("OPENAI_API_KEY")
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


def create_article_content_worker(
    project: Project,
    *,
    settings_loader: Callable[[], Mapping[str, object]] = load_settings,
):
    """Compose the article-content worker from an existing project."""
    from app.article_content_generator_worker import (
        ArticleContentGeneratorWorker,
    )

    article_path = Path(project.root) / "trabajo" / "articulo.json"
    article_data = json.loads(article_path.read_text(encoding="utf-8"))
    plan = build_article_generation_plan(article_data)

    settings = settings_loader()
    config = AIProviderConfig(
        model=str(settings.get("openai_model", "gpt-5-mini")),
        timeout_seconds=float(
            settings.get(
                "openai_timeout_seconds",
                OPENAI_DEFAULT_TIMEOUT_SECONDS,
            )
        ),
    )

    return ArticleContentGeneratorWorker(
        plan,
        "openai",
        config,
        project.root,
    )
