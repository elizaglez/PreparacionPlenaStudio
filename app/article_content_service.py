from __future__ import annotations

from app.ai.config import AIProviderConfig
from app.ai.provider_factory import create_provider
from app.generation.article_content_generator import ArticleContentGenerator
from app.generation.content_generation_request import ContentGenerationRequest
from app.generation.generated_article import GeneratedArticle


class ArticleContentService:
    """Compose an AI provider with the article content generator."""

    def __init__(
        self,
        provider_name: str,
        config: AIProviderConfig,
    ) -> None:
        provider = create_provider(provider_name, config)
        self._generator = ArticleContentGenerator(provider)

    def generate(
        self,
        request: ContentGenerationRequest,
    ) -> GeneratedArticle:
        return self._generator.generate(request)
