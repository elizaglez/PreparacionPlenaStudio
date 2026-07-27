from __future__ import annotations

from app.ai.config import AIProviderConfig
from app.article_content_service import ArticleContentService


def create_article_content_service(
    provider_name: str,
    config: AIProviderConfig,
) -> ArticleContentService:
    """Compose the article content service from application settings."""
    return ArticleContentService(provider_name, config)
