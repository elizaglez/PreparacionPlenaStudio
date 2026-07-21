from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class MasterAnswer:
    number: int
    question: str
    answer: str
    paragraph_numbers: list[int] = field(default_factory=list)
    scriptures: list[str] = field(default_factory=list)
    scripture_explanation: str = ""
    comparison: str = ""
    application: str = ""
    image_note: str = ""
    source_notes: list[str] = field(default_factory=list)
    status: str = "generated"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MasterDocument:
    title: str
    introduction: str = ""
    answers: list[MasterAnswer] = field(default_factory=list)
    conclusion: str = ""
    methodology: str = "Metodología PPA"
    model: str = ""
    generated_at: str = ""
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
