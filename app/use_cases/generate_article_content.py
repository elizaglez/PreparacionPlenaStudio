from __future__ import annotations

from app.article_content_service import ArticleContentService
from app.generation.article_generation_plan import ArticleGenerationPlan
from app.generation.content_generation_request import (
    build_content_generation_request,
)
from app.generation.generated_article import GeneratedArticle
from app.persistence.generated_article_repository import GeneratedArticleRepository


class GenerateArticleContentUseCase:
    """Generate article content through an already composed service."""

    def __init__(
        self,
        service: ArticleContentService,
        repository: GeneratedArticleRepository | None = None,
    ) -> None:
        self._service = service
        self._repository = repository

    def execute(self, plan: ArticleGenerationPlan) -> GeneratedArticle:
        request = build_content_generation_request(plan)
        article = self._service.generate(request)
        if self._repository is not None:
            self._repository.save(article)
        return article
