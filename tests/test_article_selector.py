import unittest

from app.detection.article_selector import (
    ArticleSelectionError,
    list_articles,
    select_article,
)


def page(number: int, text: str) -> dict:
    return {
        "page_number": number,
        "character_count": len(text),
        "text": text,
        "blocks": [],
        "questions": [],
        "scripture_references": [],
    }


class ArticleSelectorTests(unittest.TestCase):
    def setUp(self):
        self.pdf_result = {
            "file": "atalaya.pdf",
            "page_count": 4,
            "title": "La Atalaya",
            "author": "",
            "pages": [
                page(
                    1,
                    "\n".join(
                        [
                            "CANCIÓN 1 Cantemos",
                            "Primer artículo",
                            "TEMA",
                            "Tema del primer artículo.",
                            "1. ¿Qué aprendemos?",
                        ]
                    ),
                ),
                page(2, "Continuación del primer artículo"),
                page(
                    3,
                    "\n".join(
                        [
                            "CANCIÓN 2 Alabemos",
                            "Segundo artículo",
                            "TEMA",
                            "Tema del segundo artículo.",
                            "1. ¿Cómo lo aplicamos?",
                        ]
                    ),
                ),
                page(4, "Continuación del segundo artículo"),
            ],
            "text": "Revista completa",
        }

    def test_lists_multiple_detected_articles(self):
        articles = list_articles(self.pdf_result)

        self.assertEqual(len(articles), 2)
        self.assertEqual(
            [article["id"] for article in articles],
            ["article-1", "article-2"],
        )
        self.assertEqual(articles[0]["title"], "Primer artículo")
        self.assertEqual(articles[0]["start_page"], 1)
        self.assertEqual(articles[0]["end_page"], 2)
        self.assertEqual(articles[0]["question_count"], 1)
        self.assertEqual(articles[1]["title"], "Segundo artículo")
        self.assertEqual(articles[1]["start_page"], 3)
        self.assertEqual(articles[1]["end_page"], 4)

    def test_selects_article_by_id(self):
        articles = list_articles(self.pdf_result)

        selected = select_article(
            self.pdf_result,
            "article-2",
            candidates=articles,
        )

        self.assertEqual(selected["title"], "Segundo artículo")
        self.assertEqual(selected["page_count"], 2)
        self.assertEqual(
            [item["page_number"] for item in selected["pages"]],
            [3, 4],
        )

    def test_rejects_unknown_article_id(self):
        with self.assertRaisesRegex(
            ArticleSelectionError,
            "No existe un artículo",
        ):
            select_article(self.pdf_result, "article-99")

    def test_rejects_candidate_without_valid_pages(self):
        invalid_candidates = [
            {
                "id": "article-invalid",
                "title": "Artículo inválido",
                "start_page": 3,
                "end_page": 5,
            }
        ]

        with self.assertRaisesRegex(
            ArticleSelectionError,
            "No se pudo seleccionar",
        ):
            select_article(
                self.pdf_result,
                "article-invalid",
                candidates=invalid_candidates,
            )


if __name__ == "__main__":
    unittest.main()
