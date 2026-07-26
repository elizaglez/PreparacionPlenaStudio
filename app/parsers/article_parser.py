from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.models.article import Article, ArticleParagraph, ArticleSection
from app.parsers.scripture_parser import extract_scripture_references


class ArticleParserError(RuntimeError):
    pass


@dataclass
class ParsedArticleSection(ArticleSection):
    subtitle: str = ""
    questions: list[str] = field(default_factory=list)
    section_summary: str | None = None


@dataclass
class ParsedArticle(Article):
    review_questions: list[str] = field(default_factory=list)


PARAGRAPH_RE = re.compile(
    r"^\s*(?P<number>\d{1,2})[.)]?\s+(?P<text>\S.*)$"
)
QUESTION_START_RE = re.compile(
    r"^\s*(?P<numbers>\d{1,2}(?:\s*[-–,]\s*\d{1,2})*)[.)]\s+"
    r"(?P<question>(?:[a-z]\)\s*)?.*¿.*)$",
    re.IGNORECASE,
)
QUESTION_PREFIX_RE = re.compile(
    r"^\s*(?P<numbers>\d{1,2}(?:\s*[-–,]\s*\d{1,2})*)[.)]\s+"
    r"(?P<question>(?:[a-z]\)\s*)?.+)$",
    re.IGNORECASE,
)
QUESTION_PART_RE = re.compile(r"^[a-z]\)\s+", re.IGNORECASE)
PLAIN_QUESTION_RE = re.compile(r"^\s*(¿.+\?)\s*$")
PAGE_MARKER_RE = re.compile(
    r"^===\s*P[ÁA]GINA\s+\d+\s*===$",
    re.IGNORECASE,
)
ANSWER_LABEL_RE = re.compile(r"^Respuestas?$", re.IGNORECASE)
REVIEW_HEADING_RE = re.compile(
    r"^(?:REPASO|PREGUNTAS\s+DE\s+REPASO)$",
    re.IGNORECASE,
)
STUDY_DATE_RE = re.compile(
    r"^\d{1,2}(?:\s+DE\s+[^-]+)?-"
    r"\d{1,2}\s+DE\s+.+\s+DE\s+\d{4}$",
    re.IGNORECASE,
)
def _clean_lines(text: str) -> list[str]:
    lines: list[str] = []
    for raw in text.replace("\r", "").splitlines():
        line = re.sub(r"\s+", " ", raw).strip()
        if not line:
            continue
        if PAGE_MARKER_RE.fullmatch(line):
            continue
        if re.fullmatch(r"\d{1,3}", line):
            continue
        lines.append(line)
    return lines


def _question_numbers(value: str) -> list[int]:
    normalized = value.replace("–", "-")
    numbers: list[int] = []
    for part in re.split(r"\s*,\s*", normalized):
        if "-" in part:
            start, end = [int(v.strip()) for v in part.split("-", 1)]
            if start <= end and end - start <= 5:
                numbers.extend(range(start, end + 1))
        elif part.strip().isdigit():
            numbers.append(int(part.strip()))
    return numbers


def _looks_like_heading(line: str) -> bool:
    if len(line) < 5 or len(line) > 110:
        return False
    if "?" in line or line.endswith("."):
        return False
    letters = [character for character in line if character.isalpha()]
    return len(letters) >= 4 and all(
        character.isupper() for character in letters
    )


def _is_ignored_heading(line: str, article_title: str) -> bool:
    normalized = line.strip()
    return (
        normalized == article_title
        or normalized.upper() == "TEMA"
        or normalized.upper() == "LA ATALAYA"
        or normalized.lower().startswith("canción")
        or bool(STUDY_DATE_RE.match(normalized))
        or bool(
            re.fullmatch(
                r"(?:ENERO|FEBRERO|MARZO|ABRIL|MAYO|JUNIO|JULIO|"
                r"AGOSTO|SEPTIEMBRE|OCTUBRE|NOVIEMBRE|DICIEMBRE)"
                r"\s+DE\s+\d{4}",
                normalized,
                re.IGNORECASE,
            )
        )
        or bool(re.fullmatch(r"\([A-ZÁÉÍÓÚÜÑ. ]+\s+\d+:[^)]+\)\.?", normalized))
    )


def _subtitle_map(
    lines: list[str],
    article_title: str,
) -> dict[int, str]:
    active_subtitle = ""
    previous_was_subtitle = False
    subtitles: dict[int, str] = {}

    for line in lines:
        if REVIEW_HEADING_RE.fullmatch(line):
            break
        if _looks_like_heading(line) and not _is_ignored_heading(
            line,
            article_title,
        ):
            active_subtitle = (
                f"{active_subtitle} {line}".strip()
                if previous_was_subtitle
                else line
            )
            previous_was_subtitle = True
            continue
        if _is_ignored_heading(line, article_title):
            previous_was_subtitle = False
            continue
        previous_was_subtitle = False
        paragraph = PARAGRAPH_RE.match(line)
        if paragraph and not QUESTION_PREFIX_RE.match(line):
            subtitles[int(paragraph.group("number"))] = active_subtitle

    return subtitles


def _review_from_lines(lines: list[str]) -> tuple[list[str], int | None]:
    review_index = next(
        (
            index
            for index, line in enumerate(lines)
            if REVIEW_HEADING_RE.fullmatch(line)
        ),
        None,
    )
    if review_index is None:
        return [], None

    questions: list[str] = []
    current: list[str] = []
    for line in lines[review_index + 1:]:
        if line.lower().startswith("canción"):
            break
        numbered = QUESTION_PREFIX_RE.match(line)
        plain = PLAIN_QUESTION_RE.match(line)
        if numbered or plain:
            if current:
                questions.append(" ".join(current).strip())
            current = [
                numbered.group("question").strip()
                if numbered
                else plain.group(1).strip()
            ]
        elif current:
            current.append(line)

        if current and current[-1].rstrip().endswith("?"):
            questions.append(" ".join(current).strip())
            current = []

    if current:
        questions.append(" ".join(current).strip())
    return questions, review_index


def _find_title(lines: list[str], metadata_title: str = "") -> str:
    if metadata_title and len(metadata_title.strip()) >= 5:
        return metadata_title.strip()

    for line in lines[:35]:
        if (
            12 <= len(line) <= 150
            and not PARAGRAPH_RE.match(line)
            and not PLAIN_QUESTION_RE.match(line)
            and not line.lower().startswith(("estudio", "canción", "texto temático"))
        ):
            return line
    return "Artículo sin título detectado"


def _paragraphs_from_lines(
    lines: list[str],
    excluded_line_indexes: set[int],
    article_title: str = "",
) -> list[ArticleParagraph]:
    paragraphs: list[ArticleParagraph] = []
    current: ArticleParagraph | None = None

    for index, line in enumerate(lines):
        if index in excluded_line_indexes:
            continue

        if _looks_like_heading(line):
            continue

        match = PARAGRAPH_RE.match(line)
        if match:
            if current:
                paragraphs.append(current)
            number = int(match.group("number"))
            text = match.group("text").strip()
            current = ArticleParagraph(
                number=number,
                text=text,
                scripture_references=extract_scripture_references(text),
            )
        elif current and not _looks_like_heading(line):
            current.text = f"{current.text} {line}".strip()
            current.scripture_references = extract_scripture_references(current.text)

    if current:
        paragraphs.append(current)

    first_numbered = next(
        (paragraph for paragraph in paragraphs if paragraph.number is not None),
        None,
    )
    if first_numbered and first_numbered.number == 2:
        first_numbered_index = next(
            (
                index
                for index, line in enumerate(lines)
                if (match := PARAGRAPH_RE.match(line))
                and int(match.group("number")) == 2
            ),
            0,
        )
        initial_lines = [
            line
            for index, line in enumerate(lines[:first_numbered_index])
            if index not in excluded_line_indexes
            and line != article_title
            and not _looks_like_heading(line)
            and not STUDY_DATE_RE.match(line)
            and not line.lower().startswith(("canción", "tema"))
        ]
        initial_text = " ".join(initial_lines).strip()
        if initial_text:
            paragraphs.insert(
                0,
                ArticleParagraph(
                    number=1,
                    text=initial_text,
                    scripture_references=extract_scripture_references(
                        initial_text
                    ),
                ),
            )

    unique: dict[int, ArticleParagraph] = {}
    unnumbered: list[ArticleParagraph] = []
    for paragraph in paragraphs:
        if paragraph.number is None:
            unnumbered.append(paragraph)
        else:
            unique.setdefault(paragraph.number, paragraph)
    return list(unique.values()) + unnumbered


def _questions_from_lines(
    lines: list[str],
) -> tuple[list[dict[str, Any]], set[int]]:
    questions: list[dict[str, Any]] = []
    excluded_line_indexes: set[int] = set()
    index = 0

    while index < len(lines):
        line = lines[index]
        numbered = QUESTION_START_RE.match(line)
        if not numbered:
            prefix = QUESTION_PREFIX_RE.match(line)
            next_line = lines[index + 1] if index + 1 < len(lines) else ""
            if prefix and next_line.lstrip().startswith("¿"):
                numbered = prefix

        if numbered:
            question_parts = [numbered.group("question").strip()]
            question_indexes = [index]
            cursor = index + 1

            while cursor < len(lines):
                candidate = lines[cursor]

                if ANSWER_LABEL_RE.fullmatch(candidate):
                    excluded_line_indexes.add(cursor)
                    cursor += 1
                    break

                next_question = QUESTION_START_RE.match(candidate)
                if not next_question:
                    prefix = QUESTION_PREFIX_RE.match(candidate)
                    following = (
                        lines[cursor + 1]
                        if cursor + 1 < len(lines)
                        else ""
                    )
                    if prefix and following.lstrip().startswith("¿"):
                        next_question = prefix
                if next_question:
                    break

                if (
                    question_parts[-1].rstrip().endswith("?")
                    and not QUESTION_PART_RE.match(candidate)
                ):
                    break

                paragraph = PARAGRAPH_RE.match(candidate)
                if paragraph:
                    break

                question_parts.append(candidate)
                question_indexes.append(cursor)
                cursor += 1

            question = " ".join(question_parts).strip()
            questions.append(
                {
                    "question": question,
                    "paragraph_numbers": _question_numbers(numbered.group("numbers")),
                    "line_index": index,
                }
            )
            excluded_line_indexes.update(question_indexes)
            index = cursor
            continue

        plain = PLAIN_QUESTION_RE.match(line)
        if plain:
            previous = lines[index - 1] if index > 0 else ""
            previous_numbers = re.fullmatch(
                r"\s*(\d{1,2}(?:\s*[-–,]\s*\d{1,2})*)\s*", previous
            )
            if previous_numbers:
                questions.append(
                    {
                        "question": plain.group(1).strip(),
                        "paragraph_numbers": _question_numbers(
                            previous_numbers.group(1)
                        ),
                        "line_index": index,
                    }
                )
                excluded_line_indexes.add(index)

                if (
                    index + 1 < len(lines)
                    and ANSWER_LABEL_RE.fullmatch(lines[index + 1])
                ):
                    excluded_line_indexes.add(index + 1)

        elif ANSWER_LABEL_RE.fullmatch(line):
            excluded_line_indexes.add(index)

        index += 1

    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in questions:
        key = item["question"].lower()
        if key not in seen:
            seen.add(key)
            deduped.append(item)
    return deduped, excluded_line_indexes


def _assign_sections(
    questions: list[dict[str, Any]],
    paragraphs: list[ArticleParagraph],
    headings: list[str],
    subtitles: dict[int, str] | None = None,
) -> tuple[list[ArticleSection], list[ArticleParagraph], list[str]]:
    paragraph_map = {
        p.number: p for p in paragraphs if p.number is not None
    }
    assigned: set[int] = set()
    warnings: list[str] = []
    sections: list[ArticleSection] = []

    for index, question in enumerate(questions, start=1):
        numbers = question["paragraph_numbers"]
        selected: list[ArticleParagraph] = []

        for number in numbers:
            paragraph = paragraph_map.get(number)
            if paragraph:
                selected.append(paragraph)
                assigned.add(number)

        if not selected and index <= len(paragraphs):
            fallback = paragraphs[index - 1]
            selected = [fallback]
            if fallback.number is not None:
                assigned.add(fallback.number)
            warnings.append(
                f"No se identificaron números de párrafo para la pregunta {index}; "
                "se aplicó una asociación provisional."
            )

        references: list[str] = []
        for paragraph in selected:
            for ref in paragraph.scripture_references:
                if ref not in references:
                    references.append(ref)

        subtitle = next(
            (
                (subtitles or {}).get(number, "")
                for number in numbers
                if (subtitles or {}).get(number, "")
            ),
            "",
        )
        sections.append(
            ParsedArticleSection(
                number=index,
                question=question["question"],
                paragraph_numbers=[p.number for p in selected if p.number is not None],
                paragraphs=selected,
                scripture_references=references,
                heading=subtitle,
                subtitle=subtitle,
                questions=[question["question"]],
                section_summary=None,
            )
        )

    unassigned = [
        p for p in paragraphs
        if p.number is None or p.number not in assigned
    ]
    return sections, unassigned, warnings


def parse_article(pdf_result: dict[str, Any]) -> Article:
    text = pdf_result.get("text", "").strip()
    if not text:
        raise ArticleParserError("No hay texto del PDF para analizar.")

    lines = _clean_lines(text)
    if len(lines) < 10:
        raise ArticleParserError(
            "El texto extraído es insuficiente para estructurar el artículo."
        )

    title = _find_title(lines, pdf_result.get("title", ""))
    review_questions, review_index = _review_from_lines(lines)
    article_lines = lines[:review_index] if review_index is not None else lines
    headings = [
        line
        for line in article_lines
        if _looks_like_heading(line)
        and not _is_ignored_heading(line, title)
    ]
    subtitles = _subtitle_map(article_lines, title)
    questions, excluded_line_indexes = _questions_from_lines(article_lines)
    paragraphs = _paragraphs_from_lines(
        article_lines,
        excluded_line_indexes,
        article_title=title,
    )

    if not paragraphs:
        raise ArticleParserError(
            "No se detectaron párrafos numerados en el artículo."
        )
    if not questions:
        raise ArticleParserError(
            "No se detectaron preguntas de estudio en el artículo."
        )

    sections, unassigned, warnings = _assign_sections(
        questions,
        paragraphs,
        headings,
        subtitles,
    )

    first_numbered_index = next(
        (
            i
            for i, line in enumerate(lines)
            if PARAGRAPH_RE.match(line)
            and not _looks_like_heading(line)
        ),
        0,
    )
    introduction_lines = [
        line for line in lines[:first_numbered_index]
        if line != title
        and not _looks_like_heading(line)
        and not PLAIN_QUESTION_RE.match(line)
    ]
    introduction = " ".join(introduction_lines).strip()

    conclusion = ""
    if unassigned:
        tail = sorted(
            [p for p in unassigned if p.number is not None],
            key=lambda p: p.number or 0,
        )
        if tail:
            conclusion = " ".join(p.text for p in tail[-2:]).strip()

    if unassigned:
        warnings.append(
            f"Quedaron {len(unassigned)} párrafos sin asignar a una pregunta."
        )

    return ParsedArticle(
        title=title,
        introduction=introduction,
        sections=sections,
        conclusion=conclusion,
        detected_headings=headings,
        unassigned_paragraphs=unassigned,
        parser_warnings=warnings,
        review_questions=review_questions,
    )
