from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import fitz

from app.readers.ocr_reader import (
    OcrReadError,
    OcrUnavailableError,
    read_page_with_ocr,
)


class PdfReadError(RuntimeError):
    pass


QUESTION_RE = re.compile(
    r"^\s*(?:\d+[.)-]\s*)?.{0,220}(?:\?|¿).*$",
    re.IGNORECASE,
)
SCRIPTURE_RE = re.compile(
    r"\b(?:Génesis|Éxodo|Levítico|Números|Deuteronomio|Josué|Jueces|Rut|"
    r"1 Samuel|2 Samuel|1 Reyes|2 Reyes|1 Crónicas|2 Crónicas|Esdras|"
    r"Nehemías|Ester|Job|Salmos?|Proverbios|Eclesiastés|Cantar de los Cantares|"
    r"Isaías|Jeremías|Lamentaciones|Ezequiel|Daniel|Oseas|Joel|Amós|Abdías|"
    r"Jonás|Miqueas|Nahúm|Habacuc|Sofonías|Ageo|Zacarías|Malaquías|Mateo|"
    r"Marcos|Lucas|Juan|Hechos|Romanos|1 Corintios|2 Corintios|Gálatas|"
    r"Efesios|Filipenses|Colosenses|1 Tesalonicenses|2 Tesalonicenses|"
    r"1 Timoteo|2 Timoteo|Tito|Filemón|Hebreos|Santiago|1 Pedro|2 Pedro|"
    r"1 Juan|2 Juan|3 Juan|Judas|Apocalipsis)\s+\d+:\d+(?:-\d+)?\b",
    re.IGNORECASE,
)


def _normalize(text: str) -> str:
    text = text.replace("\u00ad", "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _extract_blocks(page: fitz.Page) -> list[dict[str, Any]]:
    blocks = []
    for block in page.get_text("blocks"):
        x0, y0, x1, y1, text, block_no, block_type = block[:7]
        clean = _normalize(text)
        if not clean:
            continue
        blocks.append(
            {
                "block_no": int(block_no),
                "type": int(block_type),
                "bbox": [round(x0, 2), round(y0, 2), round(x1, 2), round(y1, 2)],
                "text": clean,
            }
        )
    return blocks


def _detect_questions(lines: list[str]) -> list[str]:
    found: list[str] = []
    for line in lines:
        candidate = line.strip()
        if 6 <= len(candidate) <= 240 and QUESTION_RE.match(candidate):
            if candidate not in found:
                found.append(candidate)
    return found


def _detect_scriptures(text: str) -> list[str]:
    refs: list[str] = []
    for match in SCRIPTURE_RE.finditer(text):
        value = re.sub(r"\s+", " ", match.group(0)).strip()
        if value not in refs:
            refs.append(value)
    return refs


def read_pdf(path: str | Path) -> dict[str, Any]:
    pdf_path = Path(path)
    if not pdf_path.is_file():
        raise PdfReadError("No se encontró el PDF del artículo.")

    try:
        document = fitz.open(pdf_path)
    except Exception as exc:
        raise PdfReadError("El PDF no se pudo abrir.") from exc

    try:
        if document.page_count == 0:
            raise PdfReadError("El PDF no contiene páginas.")

        native_pages: list[dict[str, Any]] = []

        for index, page in enumerate(document):
            text = _normalize(page.get_text("text"))
            blocks = _extract_blocks(page)
            native_pages.append(
                {
                    "page_number": index + 1,
                    "character_count": len(text),
                    "text": text,
                    "blocks": blocks,
                }
            )

        native_character_count = sum(
            len(page["text"]) for page in native_pages
        )
        pages = native_pages

        if native_character_count == 0:
            pages = []
            for index, page in enumerate(document):
                try:
                    ocr_result = read_page_with_ocr(page)
                except OcrUnavailableError as exc:
                    raise PdfReadError(str(exc)) from exc
                except OcrReadError as exc:
                    raise PdfReadError(str(exc)) from exc
                text = _normalize(str(ocr_result.get("text", "")))
                blocks = ocr_result.get("blocks", [])
                if not isinstance(blocks, list):
                    blocks = []
                pages.append(
                    {
                        "page_number": index + 1,
                        "character_count": len(text),
                        "text": text,
                        "blocks": blocks,
                    }
                )

        all_text: list[str] = []
        all_questions: list[str] = []
        all_scriptures: list[str] = []
        for page in pages:
            text = page["text"]
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            questions = _detect_questions(lines)
            scriptures = _detect_scriptures(text)
            page["questions"] = questions
            page["scripture_references"] = scriptures

            for question in questions:
                if question not in all_questions:
                    all_questions.append(question)
            for scripture in scriptures:
                if scripture not in all_scriptures:
                    all_scriptures.append(scripture)

            all_text.append(
                f"=== PÁGINA {page['page_number']} ===\n{text}"
            )

        combined = "\n\n".join(all_text).strip()
        extracted_character_count = sum(len(page["text"]) for page in pages)
        if extracted_character_count < 50:
            raise PdfReadError(
                "El PDF casi no contiene texto reconocible."
            )

        metadata = document.metadata or {}
        return {
            "file": str(pdf_path.resolve()),
            "page_count": document.page_count,
            "title": (metadata.get("title") or "").strip(),
            "author": (metadata.get("author") or "").strip(),
            "character_count": len(combined),
            "questions": all_questions,
            "scripture_references": all_scriptures,
            "pages": pages,
            "text": combined,
        }
    finally:
        document.close()
