from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any

from app.generation.generated_article import (
    GeneratedArticle,
    GeneratedBox,
    GeneratedIntroduction,
    GeneratedQuestion,
    GeneratedSection,
)
from app.models import Project
from app.persistence.project_repository import load_project, save_project
from app.storage import save_json


GENERATED_ARTICLE_SCHEMA_VERSION = 1


class GeneratedArticleRepositoryError(RuntimeError):
    pass


class GeneratedArticleRepository(ABC):
    """Storage-independent contract for generated articles."""

    @abstractmethod
    def save(self, article: GeneratedArticle) -> None:
        raise NotImplementedError

    @abstractmethod
    def load(self) -> GeneratedArticle:
        raise NotImplementedError


class JsonGeneratedArticleRepository(GeneratedArticleRepository):
    """Persist generated articles as project-local JSON."""

    def __init__(
        self,
        project_root: str | Path,
        *,
        project: Project | None = None,
    ) -> None:
        self.project_root = Path(project_root)
        self.path = self.project_root / "trabajo" / "articulo_generado.json"
        self.project = project

    def save(self, article: GeneratedArticle) -> None:
        data = {"schema_version": GENERATED_ARTICLE_SCHEMA_VERSION}
        data.update(article.to_dict())
        save_json(self.path, data)
        project_path = self.project_root / "proyecto.json"

        project = self.project
        if project is None and project_path.is_file():
            project = load_project(project_path)
        if project is None:
            return

        previous_status = project.status
        previous_updated_at = project.updated_at
        previous_outputs = dict(project.outputs)

        project.status = "contenido_generado"
        project.updated_at = datetime.now().astimezone().isoformat(
            timespec="seconds"
        )
        project.outputs["generated_article"] = (
            "trabajo/articulo_generado.json"
        )

        try:
            save_project(project)
        except Exception:
            project.status = previous_status
            project.updated_at = previous_updated_at
            project.outputs.clear()
            project.outputs.update(previous_outputs)
            raise

    def load(self) -> GeneratedArticle:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise GeneratedArticleRepositoryError(
                "No existe articulo_generado.json."
            ) from exc
        except json.JSONDecodeError as exc:
            raise GeneratedArticleRepositoryError(
                "articulo_generado.json contiene JSON inválido."
            ) from exc

        if not isinstance(data, dict):
            raise GeneratedArticleRepositoryError(
                "articulo_generado.json no tiene la estructura esperada."
            )
        try:
            return self._from_dict(data)
        except (KeyError, TypeError, ValueError) as exc:
            raise GeneratedArticleRepositoryError(
                "articulo_generado.json no tiene la estructura esperada."
            ) from exc

    @staticmethod
    def _question(data: dict[str, Any]) -> GeneratedQuestion:
        return GeneratedQuestion(
            number=int(data["number"]),
            question=str(data["question"]),
            answer=str(data.get("answer", "")),
            application=str(data.get("application", "")),
        )

    @staticmethod
    def _box(data: dict[str, Any]) -> GeneratedBox:
        return GeneratedBox(
            title=str(data["title"]),
            explanation=str(data.get("explanation", "")),
            linked_paragraph=int(data["linked_paragraph"]),
        )

    @classmethod
    def _from_dict(cls, data: dict[str, Any]) -> GeneratedArticle:
        introduction_data = data.get("introduction", {})
        if not isinstance(introduction_data, dict):
            raise TypeError("La introducción no es un objeto.")
        sections_data = data.get("sections", [])
        if not isinstance(sections_data, list):
            raise TypeError("Las secciones no son una lista.")

        introduction = GeneratedIntroduction(
            paragraphs=list(introduction_data.get("paragraphs", [])),
            questions=[
                cls._question(question)
                for question in introduction_data.get("questions", [])
            ],
        )
        sections = [
            GeneratedSection(
                subtitle=str(section["subtitle"]),
                heygen_transition=section.get("heygen_transition"),
                questions=[
                    cls._question(question)
                    for question in section.get("questions", [])
                ],
                section_summary=section.get("section_summary"),
                boxes=[cls._box(box) for box in section.get("boxes", [])],
            )
            for section in sections_data
        ]
        return GeneratedArticle(
            title=str(data["title"]),
            introduction=introduction,
            sections=sections,
            review_questions=[
                str(question) for question in data.get("review_questions", [])
            ],
        )
