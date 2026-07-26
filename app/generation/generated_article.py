from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from typing import Any

from app.generation.article_generation_plan import ArticleGenerationPlan


@dataclass
class GeneratedQuestion:
    number: int
    question: str
    answer: str = ""
    application: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GeneratedIntroduction:
    paragraphs: list[dict[str, Any]] = field(default_factory=list)
    questions: list[GeneratedQuestion] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GeneratedBox:
    title: str
    explanation: str
    linked_paragraph: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GeneratedSection:
    subtitle: str
    heygen_transition: str | None = None
    questions: list[GeneratedQuestion] = field(default_factory=list)
    section_summary: str | None = None
    boxes: list[GeneratedBox] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GeneratedArticle:
    title: str
    introduction: GeneratedIntroduction = field(default_factory=GeneratedIntroduction)
    sections: list[GeneratedSection] = field(default_factory=list)
    review_questions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def empty_from_plan(
        cls,
        plan: ArticleGenerationPlan,
    ) -> GeneratedArticle:
        """Create an empty generated-content structure without calling AI."""
        introduction = GeneratedIntroduction()
        sections: list[GeneratedSection] = []
        for source in plan.sections:
            questions = [
                GeneratedQuestion(
                    number=question.number,
                    question=question.text,
                )
                for question in source.questions
            ]
            if source.subtitle is None:
                introduction.paragraphs.extend(deepcopy(source.paragraphs))
                introduction.questions.extend(questions)
                continue
            boxes = [
                GeneratedBox(
                    title=str(box.get("title", "")).strip(),
                    explanation="",
                    linked_paragraph=int(box.get("linked_paragraph", 0)),
                )
                for box in source.boxes
            ]
            sections.append(
                GeneratedSection(
                    subtitle=source.subtitle,
                    questions=questions,
                    boxes=boxes,
                )
            )

        return cls(
            title=plan.title,
            introduction=introduction,
            sections=sections,
            review_questions=list(plan.review_questions),
        )
