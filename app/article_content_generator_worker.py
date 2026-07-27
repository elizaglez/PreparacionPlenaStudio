from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from PySide6.QtCore import QObject, Signal, Slot

from app.ai.config import AIProviderConfig
from app.composition import create_generate_article_content_use_case
from app.generation.article_generation_plan import ArticleGenerationPlan
from app.generation.generated_article import GeneratedArticle


class ArticleContentUseCase(Protocol):
    def execute(self, plan: ArticleGenerationPlan) -> GeneratedArticle: ...


UseCaseFactory = Callable[
    [str, AIProviderConfig, str | Path],
    ArticleContentUseCase,
]


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
        project_root: str | Path,
        *,
        use_case_factory: UseCaseFactory = create_generate_article_content_use_case,
    ) -> None:
        super().__init__()
        self.plan = plan
        self.provider_name = provider_name
        self.config = config
        self.project_root = project_root
        self._use_case_factory = use_case_factory

    @Slot()
    def run(self) -> None:
        try:
            self.progress.emit(0, "Preparando generación de contenido…")
            use_case = self._use_case_factory(
                self.provider_name,
                self.config,
                self.project_root,
            )

            self.progress.emit(10, "Generando contenido del artículo…")
            result = use_case.execute(self.plan)
        except Exception:
            self.failed.emit("No se pudo generar el contenido del artículo.")
        else:
            self.progress.emit(100, "Contenido del artículo generado.")
            self.finished.emit(result)
