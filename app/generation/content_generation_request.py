from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from typing import Any

from app.generation.article_generation_plan import (
    ArticleGenerationPlan,
    GenerationSection,
)


@dataclass
class QuestionGenerationRequest:
    number: int
    question: str
    source_paragraphs: list[int] = field(default_factory=list)
    answer_required: bool = True
    application_required: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BoxGenerationRequest:
    title: str
    explanation_required: bool
    linked_paragraph: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SectionGenerationRequest:
    subtitle: str | None
    paragraphs: list[dict[str, Any]] = field(default_factory=list)
    questions: list[QuestionGenerationRequest] = field(default_factory=list)
    boxes: list[BoxGenerationRequest] = field(default_factory=list)
    needs_transition: bool = False
    needs_summary: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ContentGenerationRequest:
    article_title: str
    introduction: SectionGenerationRequest
    sections: list[SectionGenerationRequest] = field(default_factory=list)
    review_questions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _question_requests(
    source: GenerationSection,
) -> list[QuestionGenerationRequest]:
    return [
        QuestionGenerationRequest(
            number=question.number,
            question=question.text,
            source_paragraphs=list(question.paragraphs),
        )
        for question in source.questions
    ]


def _section_request(
    source: GenerationSection,
) -> SectionGenerationRequest:
    boxes = [
        BoxGenerationRequest(
            title=str(box.get("title", "")).strip(),
            explanation_required=True,
            linked_paragraph=int(box.get("linked_paragraph", 0)),
        )
        for box in source.boxes
    ]
    return SectionGenerationRequest(
        subtitle=source.subtitle,
        paragraphs=deepcopy(source.paragraphs),
        questions=_question_requests(source),
        boxes=boxes,
        needs_transition=bool(
            source.subtitle is not None and source.transition_allowed
        ),
        needs_summary=bool(source.subtitle is not None and source.summary_allowed),
    )


def build_content_generation_request(
    plan: ArticleGenerationPlan,
) -> ContentGenerationRequest:
    """Translate an article plan into generation instructions without using AI."""
    introduction = SectionGenerationRequest(subtitle=None)
    sections: list[SectionGenerationRequest] = []

    for source in plan.sections:
        request = _section_request(source)
        if source.subtitle is None:
            introduction.paragraphs.extend(request.paragraphs)
            introduction.questions.extend(request.questions)
            introduction.boxes.extend(request.boxes)
            continue
        sections.append(request)

    return ContentGenerationRequest(
        article_title=plan.title,
        introduction=introduction,
        sections=sections,
        review_questions=list(plan.review_questions),
    )
