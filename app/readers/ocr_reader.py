from __future__ import annotations

import re
from collections import defaultdict
from statistics import median
from typing import Any

import fitz


class OcrUnavailableError(RuntimeError):
    pass


class OcrReadError(RuntimeError):
    pass


NUMBERED_RE = re.compile(
    r"^\s*(\d{1,2}(?:\s*[-–,]\s*\d{1,2})*)\s*([.)])\s*(.*)$"
)
PARAGRAPH_START_RE = re.compile(r"^\s*\d{1,2}\s+\S")
QUESTION_COMMA_RE = re.compile(r"^\s*(\d{1,2})\s*[,;:]\s*(.*[¿?].*)$")
SONG_RE = re.compile(r"^CANCIÓN\s+\d+\b", re.IGNORECASE)
THEME_RE = re.compile(r"^TEMA$", re.IGNORECASE)


def _normalize(text: str) -> str:
    text = text.replace("\u00ad", "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _word_segments(words: list[tuple]) -> list[dict[str, Any]]:
    grouped: dict[tuple[int, int], list[tuple]] = defaultdict(list)
    for word in words:
        if len(word) >= 8 and str(word[4]).strip():
            grouped[(int(word[5]), int(word[6]))].append(word)

    segments: list[dict[str, Any]] = []
    for line_words in grouped.values():
        ordered = sorted(line_words, key=lambda word: float(word[0]))
        heights = [float(word[3]) - float(word[1]) for word in ordered]
        split_gap = max(10.0, median(heights) * 1.2)
        current: list[tuple] = []

        for word in ordered:
            if current and float(word[0]) - float(current[-1][2]) > split_gap:
                segments.append(_segment(current))
                current = []
            current.append(word)
        if current:
            segments.append(_segment(current))
    return segments


def _segment(words: list[tuple]) -> dict[str, Any]:
    return {
        "x0": min(float(word[0]) for word in words),
        "y0": min(float(word[1]) for word in words),
        "x1": max(float(word[2]) for word in words),
        "y1": max(float(word[3]) for word in words),
        "text": " ".join(str(word[4]).strip() for word in words),
    }


def _column_centers(segments: list[dict[str, Any]]) -> tuple[float, float] | None:
    starts = [
        segment["x0"]
        for segment in segments
        if sum(character.isalpha() for character in segment["text"]) >= 4
    ]
    if len(starts) < 4:
        return None

    left = min(starts)
    right = max(starts)
    if right - left < 40:
        return None

    for _ in range(8):
        left_group = [value for value in starts if abs(value - left) <= abs(value - right)]
        right_group = [value for value in starts if abs(value - left) > abs(value - right)]
        if not left_group or not right_group:
            return None
        left = sum(left_group) / len(left_group)
        right = sum(right_group) / len(right_group)
    return (left, right) if left < right else (right, left)


def _reading_order(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    centers = _column_centers(segments)
    if not centers:
        return sorted(segments, key=lambda item: (item["y0"], item["x0"]))

    boundary = sum(centers) / 2
    left = [item for item in segments if item["x0"] <= boundary]
    right = [item for item in segments if item["x0"] > boundary]

    paired_y: list[float] = []
    for left_item in left:
        left_height = left_item["y1"] - left_item["y0"]
        for right_item in right:
            right_height = right_item["y1"] - right_item["y0"]
            tolerance = max(left_height, right_height) * 1.5
            if abs(left_item["y0"] - right_item["y0"]) <= tolerance:
                paired_y.append(max(left_item["y0"], right_item["y0"]))

    if not paired_y:
        return sorted(segments, key=lambda item: (item["y0"], item["x0"]))

    body_start = min(paired_y)
    header = [item for item in segments if item["y0"] < body_start]
    left_body = [item for item in left if item["y0"] >= body_start]
    right_body = [item for item in right if item["y0"] >= body_start]
    return (
        sorted(header, key=lambda item: (item["y0"], item["x0"]))
        + sorted(left_body, key=lambda item: (item["y0"], item["x0"]))
        + sorted(right_body, key=lambda item: (item["y0"], item["x0"]))
    )


def _normalize_numbering(line: str) -> str:
    comma_question = QUESTION_COMMA_RE.match(line)
    if comma_question:
        line = f"{comma_question.group(1)}. {comma_question.group(2).strip()}"
    match = NUMBERED_RE.match(line)
    if not match:
        return line
    numbers = re.sub(r"\s*([-–,])\s*", r"\1 ", match.group(1)).strip()
    return f"{numbers}{match.group(2)} {match.group(3).strip()}".strip()


def _reorder_article_header(lines: list[str]) -> list[str]:
    song_index = next(
        (index for index, line in enumerate(lines) if SONG_RE.match(line)),
        None,
    )
    if song_index is None:
        return lines

    quote_index = next(
        (
            index
            for index, line in enumerate(lines[:song_index])
            if line.startswith(("“", '"', "«"))
        ),
        None,
    )
    if quote_index is None or quote_index == 0:
        return lines

    song = lines[song_index]
    after_song = song_index + 1
    if after_song < len(lines) and not THEME_RE.fullmatch(lines[after_song]):
        song = f"{song} {lines[after_song]}".strip()
        after_song += 1

    return (
        [song]
        + lines[:quote_index]
        + lines[quote_index:song_index]
        + lines[after_song:]
    )


def _structured_text(segments: list[dict[str, Any]]) -> str:
    output: list[str] = []
    question_parts: list[str] = []

    def flush_question() -> None:
        if not question_parts:
            return
        question = " ".join(question_parts).strip()
        match = NUMBERED_RE.match(question)
        if match and "¿" not in question and "?" in question:
            question = (
                f"{match.group(1)}{match.group(2)} "
                f"¿{match.group(3).strip()}"
            )
        output.extend([question, "Respuesta"])
        question_parts.clear()

    for segment in _reading_order(segments):
        line = _normalize_numbering(_normalize(segment["text"]))
        if not line:
            continue
        numbered = NUMBERED_RE.match(line)
        starts_question = bool(numbered and numbered.group(2) in ".)")

        if question_parts:
            if numbered or PARAGRAPH_START_RE.match(line) or line.isupper():
                flush_question()
            else:
                question_parts.append(line)
                continue

        if starts_question:
            question_parts.append(line)
        else:
            output.append(line)

    flush_question()
    return "\n".join(_reorder_article_header(output)).strip()


def read_page_with_ocr(
    page: fitz.Page,
    *,
    language: str = "spa",
    dpi: int = 300,
) -> dict[str, Any]:
    """Extract text and positioned blocks from one page using Tesseract OCR."""
    try:
        tessdata = fitz.get_tessdata()
    except Exception as exc:
        raise OcrUnavailableError(
            "OCR no está disponible. Instala Tesseract y el idioma español."
        ) from exc

    try:
        text_page = page.get_textpage_ocr(
            language=language,
            dpi=dpi,
            full=True,
            tessdata=tessdata,
        )
        words = page.get_text("words", textpage=text_page, sort=False)
        segments = _word_segments(words)
        text = (
            _structured_text(segments)
            if segments
            else _normalize(page.get_text("text", textpage=text_page))
        )
        raw_blocks = page.get_text("blocks", textpage=text_page)
    except Exception as exc:
        raise OcrReadError("No se pudo reconocer el texto de una página.") from exc

    blocks: list[dict[str, Any]] = []
    for block in raw_blocks:
        x0, y0, x1, y1, block_text, block_no, block_type = block[:7]
        clean = _normalize(block_text)
        if not clean:
            continue
        blocks.append(
            {
                "block_no": int(block_no),
                "type": int(block_type),
                "bbox": [
                    round(x0, 2),
                    round(y0, 2),
                    round(x1, 2),
                    round(y1, 2),
                ],
                "text": clean,
            }
        )

    return {"text": text, "blocks": blocks}
