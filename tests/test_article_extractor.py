from copy import deepcopy
import unittest

from app.detection.article_extractor import (
    ArticleExtractionError,
    extract_article,
)
from app.parsers.article_parser import parse_article


def page(
    number: int,
    text: str,
    *,
    questions: list[str] | None = None,
    references: list[str] | None = None,
) -> dict:
    return {
        "page_number": number,
        "character_count": len(text),
        "text": text,
        "blocks": [],
        "questions": questions or [],
        "scripture_references": references or [],
    }


class ArticleExtractorTests(unittest.TestCase):
    def setUp(self):
        self.pdf_result = {
            "file": "revista.pdf",
            "page_count": 5,
            "title": "La Atalaya",
            "author": "Autor",
            "character_count": 500,
            "questions": ["Pregunta exterior"],
            "scripture_references": ["Génesis 1:1"],
            "pages": [
                page(1, "Portada"),
                page(
                    2,
                    "Inicio del artículo",
                    questions=["Pregunta 1"],
                    references=["Juan 3:16"],
                ),
                page(
                    3,
                    "Continuación del artículo",
                    questions=["Pregunta 1", "Pregunta 2"],
                    references=["Juan 3:16", "Salmos 1:1"],
                ),
                page(4, "Final del artículo", questions=["Pregunta 3"]),
                page(5, "Contenido posterior"),
            ],
            "text": "Texto completo de la revista",
        }
        self.candidate = {
            "id": "article-1",
            "title": "Título seleccionado",
            "start_page": 2,
            "end_page": 4,
            "question_count": 3,
            "preview": "Inicio del artículo",
        }

    def test_extracts_selected_pages_and_recalculates_fields(self):
        result = extract_article(self.pdf_result, self.candidate)

        self.assertEqual(
            [item["page_number"] for item in result["pages"]],
            [2, 3, 4],
        )
        self.assertEqual(result["page_count"], 3)
        self.assertEqual(result["title"], "Título seleccionado")
        self.assertEqual(result["author"], "Autor")
        self.assertEqual(result["character_count"], len(result["text"]))
        self.assertEqual(
            result["questions"],
            ["Pregunta 1", "Pregunta 2", "Pregunta 3"],
        )
        self.assertEqual(
            result["scripture_references"],
            ["Juan 3:16", "Salmos 1:1"],
        )
        self.assertIn("=== PÁGINA 2 ===", result["text"])
        self.assertIn("=== PÁGINA 4 ===", result["text"])
        self.assertNotIn("Portada", result["text"])
        self.assertNotIn("Contenido posterior", result["text"])

    def test_does_not_modify_or_share_pages_with_original(self):
        original = deepcopy(self.pdf_result)

        result = extract_article(self.pdf_result, self.candidate)
        result["pages"][0]["text"] = "Texto modificado"

        self.assertEqual(self.pdf_result, original)

    def test_rejects_invalid_or_incomplete_ranges(self):
        invalid_candidates = [
            {"start_page": 4, "end_page": 2},
            {"start_page": 2},
            {"start_page": "x", "end_page": 3},
        ]

        for candidate in invalid_candidates:
            with self.subTest(candidate=candidate):
                with self.assertRaises(ArticleExtractionError):
                    extract_article(self.pdf_result, candidate)

        with self.assertRaisesRegex(
            ArticleExtractionError,
            "No se encontraron las páginas seleccionadas: 6",
        ):
            extract_article(
                self.pdf_result,
                {"start_page": 4, "end_page": 6},
            )

    def test_rejects_selected_pages_without_text(self):
        pdf_result = {
            "pages": [page(1, ""), page(2, "")],
        }

        with self.assertRaisesRegex(
            ArticleExtractionError,
            "no contienen texto extraíble",
        ):
            extract_article(
                pdf_result,
                {"start_page": 1, "end_page": 2},
            )

    def test_result_is_compatible_with_existing_article_parser(self):
        pdf_result = {
            "file": "revista.pdf",
            "title": "Título del artículo",
            "author": "",
            "pages": [
                page(
                    7,
                    """
CANCIÓN 1
Título del artículo
TEMA
Una enseñanza importante.
1. ¿Qué aprendemos del primer párrafo?
Respuesta
1 El primer párrafo contiene una enseñanza clara.
SEGUNDO PUNTO
2. ¿Qué aprendemos del segundo párrafo?
Respuesta
2 El segundo párrafo contiene otra enseñanza útil.
""",
                )
            ],
        }
        candidate = {
            "title": "Título del artículo",
            "start_page": 7,
            "end_page": 7,
        }

        extracted = extract_article(pdf_result, candidate)
        article = parse_article(extracted)

        self.assertEqual(article.title, "Título del artículo")
        self.assertEqual(len(article.sections), 2)
        self.assertEqual(article.sections[0].paragraph_numbers, [1])
        self.assertEqual(article.sections[1].paragraph_numbers, [2])


if __name__ == "__main__":
    unittest.main()
