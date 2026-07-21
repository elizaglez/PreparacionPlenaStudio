from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ArticleParagraph:
    number: int | None
    text: str
    scripture_references: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ArticleSection:
    number: int
    question: str
    paragraph_numbers: list[int] = field(default_factory=list)
    paragraphs: list[ArticleParagraph] = field(default_factory=list)
    scripture_references: list[str] = field(default_factory=list)
    heading: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Article:
    title: str
    theme_scripture: str = ""
    introduction: str = ""
    sections: list[ArticleSection] = field(default_factory=list)
    conclusion: str = ""
    detected_headings: list[str] = field(default_factory=list)
    unassigned_paragraphs: list[ArticleParagraph] = field(default_factory=list)
    parser_warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
