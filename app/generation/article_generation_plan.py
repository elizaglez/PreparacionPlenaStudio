from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from typing import Any, Mapping


class ArticleGenerationPlanError(RuntimeError):
    pass


@dataclass
class QuestionSource:
    number: int
    text: str
    paragraphs: list[int] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GenerationSection:
    subtitle: str | None
    paragraphs: list[dict[str, Any]] = field(default_factory=list)
    questions: list[QuestionSource] = field(default_factory=list)
    section_summary: str | None = None
    boxes: list[dict[str, Any]] = field(default_factory=list)
    transition_allowed: bool = False
    summary_allowed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ArticleGenerationPlan:
    title: str
    introduction: str
    sections: list[GenerationSection] = field(default_factory=list)
    review_questions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _article_data(parsed_article: Any) -> dict[str, Any]:
    if isinstance(parsed_article, Mapping):
        return deepcopy(dict(parsed_article))
    to_dict = getattr(parsed_article, "to_dict", None)
    if callable(to_dict):
        data = to_dict()
        if isinstance(data, Mapping):
            return deepcopy(dict(data))
    raise ArticleGenerationPlanError(
        "El artículo analizado no tiene una estructura compatible."
    )


def _subtitle(section: Mapping[str, Any]) -> str | None:
    value = str(section.get("subtitle", "")).strip()
    return value or None


def _question_source(
    section: Mapping[str, Any],
    fallback_number: int,
) -> QuestionSource:
    text = str(section.get("question", "")).strip()
    paragraphs = [
        int(value)
        for value in section.get("paragraph_numbers", [])
        if str(value).isdigit()
    ]
    return QuestionSource(
        number=int(section.get("number", fallback_number)),
        text=text,
        paragraphs=paragraphs,
    )


def _append_paragraphs(
    target: GenerationSection,
    paragraphs: Any,
) -> None:
    if not isinstance(paragraphs, list):
        return
    seen = {
        paragraph.get("number")
        for paragraph in target.paragraphs
        if isinstance(paragraph, dict)
    }
    for paragraph in paragraphs:
        if not isinstance(paragraph, Mapping):
            continue
        item = deepcopy(dict(paragraph))
        number = item.get("number")
        if number in seen:
            continue
        target.paragraphs.append(item)
        seen.add(number)


def _attach_boxes(
    sections: list[GenerationSection],
    boxes: Any,
) -> None:
    if not isinstance(boxes, list):
        return
    for box in boxes:
        if not isinstance(box, Mapping):
            continue
        try:
            linked_paragraph = int(box["linked_paragraph"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ArticleGenerationPlanError(
                "Un recuadro no contiene un párrafo asociado válido."
            ) from exc

        destination = next(
            (
                section
                for section in sections
                if linked_paragraph
                in {
                    paragraph.get("number")
                    for paragraph in section.paragraphs
                }
            ),
            None,
        )
        if destination is None:
            raise ArticleGenerationPlanError(
                "No se encontró la sección del recuadro vinculado al "
                f"párrafo {linked_paragraph}."
            )
        destination.boxes.append(deepcopy(dict(box)))


def build_article_generation_plan(
    parsed_article: Any,
) -> ArticleGenerationPlan:
    """Group parsed questions into generation-ready pedagogical sections."""
    article = _article_data(parsed_article)
    source_sections = article.get("sections", [])
    if not isinstance(source_sections, list):
        raise ArticleGenerationPlanError(
            "El artículo no contiene una lista de secciones válida."
        )

    sections = [GenerationSection(subtitle=None)]
    current = sections[0]

    for index, source in enumerate(source_sections, start=1):
        if not isinstance(source, Mapping):
            continue
        subtitle = _subtitle(source)
        if subtitle != current.subtitle:
            current = GenerationSection(
                subtitle=subtitle,
                transition_allowed=subtitle is not None,
            )
            sections.append(current)

        _append_paragraphs(current, source.get("paragraphs", []))
        current.questions.append(_question_source(source, index))

    titled_indexes = [
        index
        for index, section in enumerate(sections)
        if section.subtitle is not None
    ]
    for index in titled_indexes[:-1]:
        sections[index].summary_allowed = True

    _attach_boxes(sections, article.get("boxes", []))

    review_questions = article.get("review_questions", [])
    if not isinstance(review_questions, list):
        review_questions = []

    return ArticleGenerationPlan(
        title=str(article.get("title", "")).strip(),
        introduction=str(article.get("introduction", "")).strip(),
        sections=sections,
        review_questions=[
            str(question).strip()
            for question in review_questions
            if str(question).strip()
        ],
    )
