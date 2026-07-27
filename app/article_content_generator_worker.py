from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject, Signal, Slot

from app.ai.config import AIProviderConfig
from app.article_content_service import ArticleContentService
from app.composition import create_article_content_service
from app.generation.article_generation_plan import ArticleGenerationPlan


ServiceFactory = Callable[[str, AIProviderConfig], ArticleContentService]


class ArticleContentGeneratorWorker(QObject):
    """Run the new article-content generation route outside the UI thread."""

    progress = Signal(int, str)
    finished = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        plan: ArticleGenerationPlan,
        provider_name: str,
        config: AIProviderConfig,
        *,
        service_factory: ServiceFactory = create_article_content_service,
    ) -> None:
        super().__init__()
        self.plan = plan
        self.provider_name = provider_name
        self.config = config
        self._service_factory = service_factory

    @Slot()
    def run(self) -> None:
        try:
            self.progress.emit(0, "Preparando generación de contenido…")
            service = self._service_factory(self.provider_name, self.config)

            from app.use_cases.generate_article_content import (
                GenerateArticleContentUseCase,
            )

            self.progress.emit(10, "Generando contenido del artículo…")
            result = GenerateArticleContentUseCase(service).execute(self.plan)
        except Exception:
            self.failed.emit("No se pudo generar el contenido del artículo.")
        else:
            self.progress.emit(100, "Contenido del artículo generado.")
            self.finished.emit(result)
