import unittest

from app.generation.article_generation_plan import (
    ArticleGenerationPlanError,
    build_article_generation_plan,
)


def paragraph(number: int, text: str) -> dict:
    return {
        "number": number,
        "text": text,
        "scripture_references": [],
    }


def section(number: int, subtitle: str, paragraph_number: int) -> dict:
    return {
        "number": number,
        "question": f"Pregunta {number}",
        "paragraph_numbers": [paragraph_number],
        "paragraphs": [paragraph(paragraph_number, f"Párrafo {paragraph_number}")],
        "subtitle": subtitle,
    }


class ArticleGenerationPlanTests(unittest.TestCase):
    def setUp(self):
        self.article = {
            "title": "Título principal",
            "introduction": "Introducción del artículo.",
            "sections": [
                section(1, "", 1),
                section(2, "PRIMER SUBTÍTULO", 2),
                section(3, "PRIMER SUBTÍTULO", 3),
                section(4, "ÚLTIMO SUBTÍTULO", 4),
            ],
            "boxes": [
                {
                    "title": "Recuadro de reflexión",
                    "linked_paragraph": 3,
                    "content": ["Contenido complementario."],
                    "type": "reflection",
                }
            ],
            "review_questions": ["Primera pregunta", "Segunda pregunta"],
        }

    def test_builds_generation_plan_without_creating_sources(self):
        plan = build_article_generation_plan(self.article)

        self.assertEqual(plan.title, "Título principal")
        self.assertEqual(plan.introduction, "Introducción del artículo.")
        self.assertEqual(len(plan.sections), 3)

        introduction, first, last = plan.sections
        self.assertIsNone(introduction.subtitle)
        self.assertFalse(introduction.transition_allowed)
        self.assertFalse(introduction.summary_allowed)
        self.assertEqual([item.number for item in introduction.questions], [1])

        self.assertEqual(first.subtitle, "PRIMER SUBTÍTULO")
        self.assertTrue(first.transition_allowed)
        self.assertTrue(first.summary_allowed)
        self.assertIsNone(first.section_summary)
        self.assertEqual(
            [item["number"] for item in first.paragraphs],
            [2, 3],
        )
        self.assertEqual(
            [item.number for item in first.questions],
            [2, 3],
        )
        self.assertEqual(first.questions[1].text, "Pregunta 3")
        self.assertEqual(first.questions[1].paragraphs, [3])
        self.assertEqual(first.boxes, self.article["boxes"])

        self.assertEqual(last.subtitle, "ÚLTIMO SUBTÍTULO")
        self.assertTrue(last.transition_allowed)
        self.assertFalse(last.summary_allowed)
        self.assertIsNone(last.section_summary)
        self.assertEqual(plan.review_questions, self.article["review_questions"])

        source_question_count = len(self.article["sections"])
        plan_question_count = sum(
            len(item.questions) for item in plan.sections
        )
        self.assertEqual(plan_question_count, source_question_count)
        self.assertEqual(
            sum(len(item.paragraphs) for item in plan.sections),
            4,
        )

    def test_groups_only_consecutive_matching_subtitles(self):
        article = dict(self.article)
        article["boxes"] = []
        article["sections"] = [
            section(1, "", 1),
            section(2, "SUBTÍTULO A", 2),
            section(3, "SUBTÍTULO B", 3),
            section(4, "SUBTÍTULO A", 4),
        ]

        plan = build_article_generation_plan(article)

        self.assertEqual(
            [item.subtitle for item in plan.sections],
            [None, "SUBTÍTULO A", "SUBTÍTULO B", "SUBTÍTULO A"],
        )
        self.assertEqual(
            [item.summary_allowed for item in plan.sections],
            [False, True, True, False],
        )

    def test_rejects_box_without_matching_paragraph(self):
        article = dict(self.article)
        article["boxes"] = [
            {
                "title": "Recuadro huérfano",
                "linked_paragraph": 99,
                "content": [],
                "type": "reflection",
            }
        ]

        with self.assertRaisesRegex(
            ArticleGenerationPlanError,
            "párrafo 99",
        ):
            build_article_generation_plan(article)


if __name__ == "__main__":
    unittest.main()
