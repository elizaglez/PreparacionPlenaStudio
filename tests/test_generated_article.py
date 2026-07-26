import unittest

from app.generation.article_generation_plan import (
    ArticleGenerationPlan,
    GenerationSection,
    QuestionSource,
)
from app.generation.generated_article import (
    GeneratedArticle,
    GeneratedBox,
    GeneratedIntroduction,
    GeneratedQuestion,
    GeneratedSection,
)


class GeneratedArticleTests(unittest.TestCase):
    def test_creates_empty_generated_article_from_plan(self):
        plan = ArticleGenerationPlan(
            title="Título principal",
            introduction="Introducción.",
            sections=[
                GenerationSection(
                    subtitle=None,
                    paragraphs=[
                        {"number": 1, "text": "Primer párrafo"},
                        {"number": 2, "text": "Segundo párrafo"},
                    ],
                    questions=[
                        QuestionSource(
                            number=1,
                            text="Pregunta introductoria",
                            paragraphs=[1, 2],
                        )
                    ],
                ),
                GenerationSection(
                    subtitle="PRIMER SUBTÍTULO",
                    questions=[
                        QuestionSource(
                            number=2,
                            text="Pregunta principal",
                            paragraphs=[3],
                        )
                    ],
                    boxes=[
                        {
                            "title": "Recuadro de reflexión",
                            "linked_paragraph": 3,
                            "content": ["Contenido fuente"],
                            "type": "reflection",
                        }
                    ],
                    transition_allowed=True,
                    summary_allowed=True,
                ),
                GenerationSection(
                    subtitle="ÚLTIMO SUBTÍTULO",
                    questions=[
                        QuestionSource(
                            number=3,
                            text="Pregunta final",
                            paragraphs=[4],
                        )
                    ],
                    transition_allowed=True,
                    summary_allowed=False,
                ),
            ],
            review_questions=["Pregunta de repaso"],
        )

        generated = GeneratedArticle.empty_from_plan(plan)

        self.assertEqual(generated.title, "Título principal")
        self.assertFalse(hasattr(generated, "heygen_transition"))
        self.assertEqual(
            generated.introduction.paragraphs,
            [
                {"number": 1, "text": "Primer párrafo"},
                {"number": 2, "text": "Segundo párrafo"},
            ],
        )
        self.assertEqual(len(generated.introduction.questions), 1)
        introduction_question = generated.introduction.questions[0]
        self.assertEqual(introduction_question.number, 1)
        self.assertEqual(introduction_question.question, "Pregunta introductoria")
        self.assertEqual(introduction_question.answer, "")
        self.assertEqual(introduction_question.application, "")
        self.assertEqual(len(generated.sections), 2)
        self.assertEqual(
            [section.subtitle for section in generated.sections],
            ["PRIMER SUBTÍTULO", "ÚLTIMO SUBTÍTULO"],
        )
        self.assertIsNone(generated.sections[0].heygen_transition)
        self.assertIsNone(generated.sections[0].section_summary)

        question = generated.sections[0].questions[0]
        self.assertEqual(question.number, 2)
        self.assertEqual(question.question, "Pregunta principal")
        self.assertEqual(question.answer, "")
        self.assertEqual(question.application, "")

        box = generated.sections[0].boxes[0]
        self.assertEqual(box.title, "Recuadro de reflexión")
        self.assertEqual(box.explanation, "")
        self.assertEqual(box.linked_paragraph, 3)
        self.assertEqual(generated.review_questions, ["Pregunta de repaso"])

    def test_serializes_generated_models(self):
        generated = GeneratedArticle(
            title="Título",
            introduction=GeneratedIntroduction(
                paragraphs=[{"number": 1, "text": "Introducción"}],
                questions=[
                    GeneratedQuestion(
                        number=1,
                        question="Pregunta introductoria",
                    )
                ],
            ),
            sections=[
                GeneratedSection(
                    subtitle="SUBTÍTULO",
                    heygen_transition="Transición",
                    questions=[
                        GeneratedQuestion(
                            number=1,
                            question="Pregunta",
                            answer="Respuesta",
                            application="Aplicación",
                        )
                    ],
                    section_summary="Resumen",
                    boxes=[
                        GeneratedBox(
                            title="Recuadro",
                            explanation="Explicación",
                            linked_paragraph=1,
                        )
                    ],
                )
            ],
            review_questions=["Repaso"],
        )

        data = generated.to_dict()

        self.assertEqual(data["introduction"]["paragraphs"][0]["number"], 1)
        self.assertEqual(
            data["introduction"]["questions"][0]["question"],
            "Pregunta introductoria",
        )
        self.assertEqual(data["sections"][0]["questions"][0]["answer"], "Respuesta")
        self.assertEqual(data["sections"][0]["boxes"][0]["linked_paragraph"], 1)
        self.assertEqual(data["review_questions"], ["Repaso"])


if __name__ == "__main__":
    unittest.main()
