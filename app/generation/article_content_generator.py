from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.ai.provider import AIProvider
from app.generation.content_generation_request import (
    ContentGenerationRequest,
    QuestionGenerationRequest,
    SectionGenerationRequest,
)
from app.generation.generated_article import (
    GeneratedArticle,
    GeneratedBox,
    GeneratedIntroduction,
    GeneratedQuestion,
    GeneratedSection,
)


class ArticleContentGenerator:
    """Generate article content through an injected AI provider."""

    def __init__(self, provider: AIProvider) -> None:
        self._provider = provider

    @staticmethod
    def _paragraph_text(paragraph: dict[str, Any]) -> str:
        return str(paragraph.get("text", "")).strip()

    def _question(
        self,
        source: QuestionGenerationRequest,
        paragraphs: list[dict[str, Any]],
    ) -> GeneratedQuestion:
        paragraph_numbers = set(source.source_paragraphs)
        context = [
            text
            for paragraph in paragraphs
            if paragraph.get("number") in paragraph_numbers
            if (text := self._paragraph_text(paragraph))
        ]
        answer = (
            self._provider.generate_answer(source.question, context)
            if source.answer_required
            else ""
        )
        application = (
            self._provider.generate_application(answer)
            if source.application_required
            else ""
        )
        return GeneratedQuestion(
            number=source.number,
            question=source.question,
            answer=answer,
            application=application,
        )

    def _questions(
        self,
        source: SectionGenerationRequest,
    ) -> list[GeneratedQuestion]:
        return [
            self._question(question, source.paragraphs)
            for question in source.questions
        ]

    def _section(self, source: SectionGenerationRequest) -> GeneratedSection:
        subtitle = source.subtitle or ""
        section_content = "\n\n".join(
            text
            for paragraph in source.paragraphs
            if (text := self._paragraph_text(paragraph))
        )
        return GeneratedSection(
            subtitle=subtitle,
            heygen_transition=(
                self._provider.generate_heygen_transition(subtitle)
                if source.needs_transition
                else None
            ),
            questions=self._questions(source),
            section_summary=(
                self._provider.generate_summary(section_content)
                if source.needs_summary
                else None
            ),
            boxes=[
                GeneratedBox(
                    title=box.title,
                    explanation=(
                        self._provider.generate_box_explanation(box.title)
                        if box.explanation_required
                        else ""
                    ),
                    linked_paragraph=box.linked_paragraph,
                )
                for box in source.boxes
            ],
        )

    def generate(self, request: ContentGenerationRequest) -> GeneratedArticle:
        """Convert generation instructions into provider-generated content."""
        introduction = GeneratedIntroduction(
            paragraphs=deepcopy(request.introduction.paragraphs),
            questions=self._questions(request.introduction),
        )
        return GeneratedArticle(
            title=request.article_title,
            introduction=introduction,
            sections=[self._section(section) for section in request.sections],
            review_questions=list(request.review_questions),
        )
