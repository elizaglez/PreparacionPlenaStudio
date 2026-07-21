from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


class MasterValidationError(RuntimeError):
    pass


@dataclass
class ValidationIssue:
    level: str
    code: str
    message: str
    answer_number: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ValidationReport:
    valid: bool
    issues: list[ValidationIssue] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "issues": [issue.to_dict() for issue in self.issues],
        }


def _normalized(text: str) -> str:
    return " ".join(str(text).split()).strip()


def validate_master(article: dict[str, Any], master: dict[str, Any]) -> ValidationReport:
    issues: list[ValidationIssue] = []

    sections = article.get("sections", [])
    answers = master.get("answers", [])

    if not isinstance(sections, list) or not sections:
        issues.append(
            ValidationIssue(
                "error",
                "ARTICLE_WITHOUT_SECTIONS",
                "El artículo no contiene preguntas estructuradas.",
            )
        )
        return ValidationReport(valid=False, issues=issues)

    if not isinstance(answers, list):
        issues.append(
            ValidationIssue(
                "error",
                "MASTER_ANSWERS_INVALID",
                "El campo answers del MASTER no es una lista.",
            )
        )
        return ValidationReport(valid=False, issues=issues)

    if len(answers) != len(sections):
        issues.append(
            ValidationIssue(
                "error",
                "ANSWER_COUNT_MISMATCH",
                (
                    f"El artículo contiene {len(sections)} preguntas, pero el "
                    f"MASTER contiene {len(answers)} respuestas."
                ),
            )
        )

    article_by_number = {
        int(section.get("number", index + 1)): section
        for index, section in enumerate(sections)
    }
    answer_numbers: set[int] = set()

    for index, answer in enumerate(answers, start=1):
        number = int(answer.get("number", index))
        if number in answer_numbers:
            issues.append(
                ValidationIssue(
                    "error",
                    "DUPLICATE_ANSWER_NUMBER",
                    f"La respuesta {number} está duplicada.",
                    number,
                )
            )
        answer_numbers.add(number)

        section = article_by_number.get(number)
        if section is None:
            issues.append(
                ValidationIssue(
                    "error",
                    "ORPHAN_ANSWER",
                    f"La respuesta {number} no corresponde a ninguna pregunta.",
                    number,
                )
            )
            continue

        original_question = _normalized(section.get("question", ""))
        master_question = _normalized(answer.get("question", ""))
        if original_question != master_question:
            issues.append(
                ValidationIssue(
                    "error",
                    "QUESTION_CHANGED",
                    "La pregunta no se conservó literalmente.",
                    number,
                )
            )

        if not _normalized(answer.get("answer", "")):
            issues.append(
                ValidationIssue(
                    "error",
                    "EMPTY_ANSWER",
                    "La respuesta principal está vacía.",
                    number,
                )
            )

        original_refs = {
            _normalized(value)
            for value in section.get("scripture_references", [])
            if _normalized(value)
        }
        master_refs = {
            _normalized(value)
            for value in answer.get("scriptures", [])
            if _normalized(value)
        }
        missing_refs = original_refs - master_refs
        if missing_refs:
            issues.append(
                ValidationIssue(
                    "warning",
                    "SCRIPTURES_LOST",
                    (
                        "Se perdieron referencias bíblicas detectadas: "
                        + ", ".join(sorted(missing_refs))
                    ),
                    number,
                )
            )

    for number in article_by_number:
        if number not in answer_numbers:
            issues.append(
                ValidationIssue(
                    "error",
                    "MISSING_ANSWER",
                    f"No existe respuesta para la pregunta {number}.",
                    number,
                )
            )

    valid = not any(issue.level == "error" for issue in issues)
    return ValidationReport(valid=valid, issues=issues)


def assert_valid_master(article: dict[str, Any], master: dict[str, Any]) -> None:
    report = validate_master(article, master)
    if report.valid:
        return

    messages = [
        f"[{issue.code}] {issue.message}"
        for issue in report.issues
        if issue.level == "error"
    ]
    raise MasterValidationError(
        "El MASTER no superó la validación:\n" + "\n".join(messages)
    )
