from __future__ import annotations

from app.article_content_service import ArticleContentService
from app.generation.article_generation_plan import ArticleGenerationPlan
from app.generation.content_generation_request import (
    build_content_generation_request,
)
from app.generation.generated_article import GeneratedArticle


class GenerateArticleContentUseCase:
    """Generate article content through an already composed service."""

    def __init__(self, service: ArticleContentService) -> None:
        self._service = service

    def execute(self, plan: ArticleGenerationPlan) -> GeneratedArticle:
        request = build_content_generation_request(plan)
        return self._service.generate(request)
