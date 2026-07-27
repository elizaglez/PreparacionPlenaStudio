from __future__ import annotations

from app.ai.config import AIProviderConfig
from app.ai.provider import AIProvider
from app.ai.provider_factory import create_provider
from app.generation.article_content_generator import ArticleContentGenerator
from app.generation.content_generation_request import ContentGenerationRequest
from app.generation.generated_article import GeneratedArticle


class ArticleContentService:
    """Compose an AI provider with the article content generator."""

    def __init__(
        self,
        provider: AIProvider | str,
        config: AIProviderConfig | None = None,
    ) -> None:
        resolved_provider = provider
        if isinstance(provider, str):
            if config is None:
                raise TypeError(
                    "config es obligatorio cuando el proveedor se indica "
                    "por nombre."
                )
            resolved_provider = create_provider(provider, config)
        self._generator = ArticleContentGenerator(resolved_provider)

    def generate(
        self,
        request: ContentGenerationRequest,
    ) -> GeneratedArticle:
        return self._generator.generate(request)
