import unittest

from app.detection.article_detector import detect_articles


def page(number: int, text: str) -> dict:
    return {
        "page_number": number,
        "character_count": len(text),
        "text": text,
        "blocks": [],
        "questions": [],
        "scripture_references": [],
    }


class ArticleDetectorTests(unittest.TestCase):
    def test_detects_multiple_study_articles(self):
        pdf_result = {
            "pages": [
                page(1, "Portada de La Atalaya"),
                page(2, "Índice y contenido editorial"),
                page(
                    3,
                    """
27 DE JULIO-2 DE AGOSTO DE 2026
CANCIÓN 56 Vive la verdad
Cuida tu espiritualidad mientras cursas estudios adicionales
“Sigamos andando correctamente por ese mismo camino”.
TEMA
Cuatro principios bíblicos que pueden ayudarte.
1, 2. a) Si continúas estudiando, ¿de qué tendrás que asegurarte?
""",
                ),
                page(4, "3. Mientras estudias, ¿con qué debes tener cuidado?"),
                page(5, "Conclusión del primer artículo"),
                page(
                    6,
                    """
3-9 DE AGOSTO DE 2026
CANCIÓN 12 Una esperanza segura
Mantengamos firme nuestra esperanza
“Mantengan firmemente su esperanza”.
TEMA
Cómo fortalecer nuestra esperanza.
1. ¿Por qué necesitamos una esperanza firme?
""",
                ),
                page(7, "2. ¿Qué nos ayudará a mantenerla?"),
                page(8, "Conclusión del segundo artículo"),
            ]
        }

        candidates = detect_articles(pdf_result)

        self.assertEqual(len(candidates), 2)
        self.assertEqual(candidates[0]["id"], "article-1")
        self.assertEqual(
            candidates[0]["title"],
            "Cuida tu espiritualidad mientras cursas estudios adicionales",
        )
        self.assertEqual(candidates[0]["start_page"], 3)
        self.assertEqual(candidates[0]["end_page"], 5)
        self.assertEqual(candidates[0]["question_count"], 2)
        self.assertIn("Cuida tu espiritualidad", candidates[0]["preview"])

        self.assertEqual(candidates[1]["id"], "article-2")
        self.assertEqual(
            candidates[1]["title"],
            "Mantengamos firme nuestra esperanza",
        )
        self.assertEqual(candidates[1]["start_page"], 6)
        self.assertEqual(candidates[1]["end_page"], 8)
        self.assertEqual(candidates[1]["question_count"], 2)

    def test_counts_question_when_it_continues_on_next_line(self):
        pdf_result = {
            "pages": [
                page(
                    5,
                    """
ARTÍCULO DE ESTUDIO 30
CANCIÓN 10 Jehová es nuestro refugio
Confiemos siempre en Jehová
“Él es nuestro refugio”.
TEMA
Razones para confiar en Jehová.
1. ¿Por qué debemos seguir confiando
en Jehová durante las pruebas?
""",
                ),
                page(6, "2. ¿Cómo demostramos esa confianza?"),
            ]
        }

        candidates = detect_articles(pdf_result)

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["question_count"], 2)

    def test_ignores_incomplete_start_signature(self):
        pdf_result = {
            "pages": [
                page(
                    1,
                    """
Programa especial
CANCIÓN 15 Cantemos juntos
Información general sin marcador de tema.
""",
                )
            ]
        }

        self.assertEqual(detect_articles(pdf_result), [])

    def test_returns_empty_list_without_pages(self):
        self.assertEqual(detect_articles({}), [])
        self.assertEqual(detect_articles({"pages": []}), [])


if __name__ == "__main__":
    unittest.main()
