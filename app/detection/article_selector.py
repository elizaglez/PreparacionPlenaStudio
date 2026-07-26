from __future__ import annotations

from typing import Any

from app.detection.article_detector import detect_articles
from app.detection.article_extractor import (
    ArticleExtractionError,
    extract_article,
)


class ArticleSelectionError(RuntimeError):
    pass


def list_articles(pdf_result: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the article candidates available for selection."""
    return detect_articles(pdf_result)


def select_article(
    pdf_result: dict[str, Any],
    article_id: str,
    candidates: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Select an article candidate by id and return its extracted PDF result."""
    available = list_articles(pdf_result) if candidates is None else candidates
    candidate = next(
        (
            item
            for item in available
            if isinstance(item, dict) and item.get("id") == article_id
        ),
        None,
    )
    if candidate is None:
        raise ArticleSelectionError(
            f"No existe un artículo con el id {article_id!r}."
        )

    try:
        return extract_article(pdf_result, candidate)
    except ArticleExtractionError as exc:
        raise ArticleSelectionError(
            f"No se pudo seleccionar el artículo {article_id!r}: {exc}"
        ) from exc
