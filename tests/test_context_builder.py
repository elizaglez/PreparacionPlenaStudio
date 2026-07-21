import unittest

from app.context.context_builder import ContextBuilder


class ContextBuilderTests(unittest.TestCase):
    def test_includes_neighbor_questions(self):
        article = {
            "title": "Artículo",
            "introduction": "Introducción",
            "sections": [
                {
                    "number": 1,
                    "question": "¿Primera?",
                    "paragraphs": [],
                    "scripture_references": [],
                },
                {
                    "number": 2,
                    "question": "¿Segunda?",
                    "paragraphs": [],
                    "scripture_references": [],
                },
                {
                    "number": 3,
                    "question": "¿Tercera?",
                    "paragraphs": [],
                    "scripture_references": [],
                },
            ],
        }

        context = ContextBuilder(article, "").build(1)
        self.assertEqual(context.previous_question, "¿Primera?")
        self.assertEqual(context.next_question, "¿Tercera?")
        self.assertEqual(context.question, "¿Segunda?")

    def test_builds_paragraph_text(self):
        article = {
            "title": "Artículo",
            "sections": [
                {
                    "number": 1,
                    "question": "¿Pregunta?",
                    "paragraphs": [
                        {"number": 1, "text": "Texto del párrafo."}
                    ],
                    "scripture_references": [],
                }
            ],
        }

        context = ContextBuilder(article, "").build(0)
        self.assertIn("Párrafo 1:", context.paragraph_text)


if __name__ == "__main__":
    unittest.main()
