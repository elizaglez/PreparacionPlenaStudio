from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class QuestionContext:
    article_title: str
    article_introduction: str
    question_number: int
    question: str
    paragraph_text: str
    scripture_references: list[str] = field(default_factory=list)
    bible_context: str = ""
    previous_question: str = ""
    next_question: str = ""
    heading: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ContextBuilder:
    def __init__(self, article: dict[str, Any], bible_text: str):
        self.article = article
        self.bible_text = bible_text or ""
        self.sections = article.get("sections", [])

    def build(self, section_index: int) -> QuestionContext:
        section = self.sections[section_index]
        references = [
            str(value)
            for value in section.get("scripture_references", [])
            if str(value).strip()
        ]

        previous_question = ""
        next_question = ""
        if section_index > 0:
            previous_question = str(
                self.sections[section_index - 1].get("question", "")
            ).strip()
        if section_index + 1 < len(self.sections):
            next_question = str(
                self.sections[section_index + 1].get("question", "")
            ).strip()

        return QuestionContext(
            article_title=str(self.article.get("title", "")).strip(),
            article_introduction=str(
                self.article.get("introduction", "")
            ).strip(),
            question_number=int(section.get("number", section_index + 1)),
            question=str(section.get("question", "")).strip(),
            paragraph_text=self._paragraph_text(section),
            scripture_references=references,
            bible_context=self._bible_context(references),
            previous_question=previous_question,
            next_question=next_question,
            heading=str(section.get("heading", "")).strip(),
        )

    @staticmethod
    def _paragraph_text(section: dict[str, Any]) -> str:
        blocks: list[str] = []
        for paragraph in section.get("paragraphs", []):
            number = paragraph.get("number")
            prefix = f"Párrafo {number}: " if number is not None else ""
            text = str(paragraph.get("text", "")).strip()
            if text:
                blocks.append(prefix + text)
        return "\n".join(blocks)

    def _bible_context(self, references: list[str]) -> str:
        if not references or not self.bible_text.strip():
            return ""

        lines = [
            line.strip()
            for line in self.bible_text.splitlines()
            if line.strip()
        ]
        selected: list[str] = []

        for reference in references:
            book_chapter = reference.split(":")[0].lower()
            book = re.sub(r"\s+\d+$", "", book_chapter).strip()
            chapter = book_chapter.removeprefix(book).strip()
            terms = [
                reference.lower(),
                book_chapter,
                f"{book} {chapter}".strip(),
            ]

            for index, line in enumerate(lines):
                low = line.lower()
                if any(term and term in low for term in terms):
                    start = max(0, index - 1)
                    end = min(len(lines), index + 3)
                    excerpt = " ".join(lines[start:end])
                    if excerpt not in selected:
                        selected.append(excerpt)
                    break

        return "\n".join(selected)
