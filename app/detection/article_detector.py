from __future__ import annotations

import re
from typing import Any


SONG_RE = re.compile(r"^CANCIÓN\s+\d+\b", re.IGNORECASE)
THEME_RE = re.compile(r"^TEMA$", re.IGNORECASE)
DATE_RE = re.compile(
    r"^\d{1,2}\s+DE\s+.+-\d{1,2}\s+DE\s+.+\s+DE\s+\d{4}$",
    re.IGNORECASE,
)
STUDY_ARTICLE_RE = re.compile(
    r"^ARTÍCULO\s+DE\s+ESTUDIO\s+\d+\b",
    re.IGNORECASE,
)
STUDY_QUESTION_RE = re.compile(
    r"^\s*\d{1,2}(?:\s*[-–,]\s*\d{1,2})*[.)]\s+"
    r"(?:[a-z]\)\s*)?.*¿",
    re.IGNORECASE,
)
OPENING_QUOTE_RE = re.compile(r'^[“"«]')


def _lines(page: dict[str, Any]) -> list[str]:
    return [
        re.sub(r"\s+", " ", line).strip()
        for line in str(page.get("text", "")).splitlines()
        if line.strip()
    ]


def _title_from_lines(lines: list[str], song_index: int) -> str:
    quote_index = next(
        (
            index
            for index in range(song_index - 1, -1, -1)
            if OPENING_QUOTE_RE.match(lines[index])
        ),
        None,
    )
    if quote_index is None:
        quote_index = next(
            (
                index
                for index in range(song_index - 1, -1, -1)
                if DATE_RE.match(lines[index])
            ),
            song_index,
        )

    title_parts: list[str] = []
    for line in reversed(lines[max(0, quote_index - 4):quote_index]):
        if (
            STUDY_ARTICLE_RE.match(line)
            or STUDY_QUESTION_RE.match(line)
            or re.match(r"^\d{1,2}[.)]?\s+", line)
            or (title_parts and "?" in line and "¿" not in line)
        ):
            break
        title_parts.append(line)

    return " ".join(reversed(title_parts)).strip()


def _start_candidate(page: dict[str, Any]) -> dict[str, Any] | None:
    lines = _lines(page)
    song_index = next(
        (index for index, line in enumerate(lines) if SONG_RE.match(line)),
        None,
    )
    if song_index is None:
        return None

    theme_index = next(
        (
            index
            for index, line in enumerate(lines[song_index + 1:], song_index + 1)
            if THEME_RE.fullmatch(line)
        ),
        None,
    )
    if theme_index is None or theme_index - song_index > 15:
        return None

    title = _title_from_lines(lines, song_index)
    if not title:
        return None

    return {
        "title": title,
        "start_page": int(page.get("page_number", 0)),
        "has_heading": any(
            DATE_RE.match(line) or STUDY_ARTICLE_RE.match(line)
            for line in lines[:song_index]
        ),
    }


def _question_count(pages: list[dict[str, Any]]) -> int:
    questions: set[str] = set()
    for page in pages:
        for line in _lines(page):
            if STUDY_QUESTION_RE.match(line):
                questions.add(line.casefold())
    return len(questions)


def _preview(pages: list[dict[str, Any]], limit: int = 240) -> str:
    text = " ".join(
        re.sub(r"\s+", " ", str(page.get("text", ""))).strip()
        for page in pages
    ).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def detect_articles(pdf_result: dict[str, Any]) -> list[dict[str, Any]]:
    """Return probable study-article ranges from a complete PDF result."""
    pages = pdf_result.get("pages", [])
    if not isinstance(pages, list) or not pages:
        return []

    ordered_pages = sorted(
        (page for page in pages if isinstance(page, dict)),
        key=lambda page: int(page.get("page_number", 0)),
    )

    starts: list[dict[str, Any]] = []
    for page_index, page in enumerate(ordered_pages):
        candidate = _start_candidate(page)
        if candidate:
            candidate["page_index"] = page_index
            starts.append(candidate)

    candidates: list[dict[str, Any]] = []
    for index, start in enumerate(starts):
        start_index = int(start["page_index"])
        end_index = (
            int(starts[index + 1]["page_index"]) - 1
            if index + 1 < len(starts)
            else len(ordered_pages) - 1
        )
        candidate_pages = ordered_pages[start_index:end_index + 1]
        if not candidate_pages:
            continue

        candidates.append(
            {
                "id": f"article-{index + 1}",
                "title": str(start["title"]),
                "start_page": int(candidate_pages[0].get("page_number", 0)),
                "end_page": int(candidate_pages[-1].get("page_number", 0)),
                "question_count": _question_count(candidate_pages),
                "preview": _preview(candidate_pages),
            }
        )

    return candidates
