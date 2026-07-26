from __future__ import annotations

from copy import deepcopy
from typing import Any


class ArticleExtractionError(RuntimeError):
    pass


def _ordered_unique(values: list[Any]) -> list[Any]:
    unique: list[Any] = []
    for value in values:
        if value not in unique:
            unique.append(value)
    return unique


def extract_article(
    pdf_result: dict[str, Any],
    candidate: dict[str, Any],
) -> dict[str, Any]:
    """Build a parser-compatible PDF result for the selected article."""
    pages = pdf_result.get("pages", [])
    if not isinstance(pages, list) or not pages:
        raise ArticleExtractionError("El PDF no contiene páginas extraídas.")

    try:
        start_page = int(candidate["start_page"])
        end_page = int(candidate["end_page"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ArticleExtractionError(
            "El artículo seleccionado no contiene límites válidos."
        ) from exc

    if start_page < 1 or end_page < start_page:
        raise ArticleExtractionError(
            "El rango de páginas del artículo seleccionado no es válido."
        )

    page_map: dict[int, dict[str, Any]] = {}
    for page in pages:
        if not isinstance(page, dict):
            continue
        try:
            page_number = int(page.get("page_number", 0))
        except (TypeError, ValueError):
            continue
        page_map.setdefault(page_number, page)

    expected_numbers = list(range(start_page, end_page + 1))
    missing = [number for number in expected_numbers if number not in page_map]
    if missing:
        missing_text = ", ".join(str(number) for number in missing)
        raise ArticleExtractionError(
            f"No se encontraron las páginas seleccionadas: {missing_text}."
        )

    selected_pages = deepcopy(
        [page_map[number] for number in expected_numbers]
    )
    if not any(str(page.get("text", "")).strip() for page in selected_pages):
        raise ArticleExtractionError(
            "Las páginas seleccionadas no contienen texto extraíble."
        )

    combined_text = "\n\n".join(
        f"=== PÁGINA {page['page_number']} ===\n"
        f"{str(page.get('text', '')).strip()}"
        for page in selected_pages
    ).strip()

    questions = _ordered_unique(
        [
            question
            for page in selected_pages
            for question in (
                page.get("questions", [])
                if isinstance(page.get("questions", []), list)
                else []
            )
        ]
    )
    scripture_references = _ordered_unique(
        [
            reference
            for page in selected_pages
            for reference in (
                page.get("scripture_references", [])
                if isinstance(page.get("scripture_references", []), list)
                else []
            )
        ]
    )

    title = str(candidate.get("title", "")).strip()
    if not title:
        title = str(pdf_result.get("title", "")).strip()

    return {
        "file": str(pdf_result.get("file", "")),
        "page_count": len(selected_pages),
        "title": title,
        "author": str(pdf_result.get("author", "")),
        "character_count": len(combined_text),
        "questions": questions,
        "scripture_references": scripture_references,
        "pages": selected_pages,
        "text": combined_text,
    }
