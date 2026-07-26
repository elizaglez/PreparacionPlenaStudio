import unittest

from app.generation.article_generation_plan import (
    ArticleGenerationPlan,
    GenerationSection,
    QuestionSource,
)
from app.generation.content_generation_request import (
    BoxGenerationRequest,
    ContentGenerationRequest,
    QuestionGenerationRequest,
    SectionGenerationRequest,
    build_content_generation_request,
)


class ContentGenerationRequestTests(unittest.TestCase):
    def test_builds_generation_instructions_from_plan(self):
        introduction_paragraph = {"number": 1, "text": "Introducción"}
        plan = ArticleGenerationPlan(
            title="Título principal",
            introduction="Texto introductorio",
            sections=[
                GenerationSection(
                    subtitle=None,
                    paragraphs=[introduction_paragraph],
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
                    paragraphs=[{"number": 3, "text": "Contenido"}],
                    questions=[
                        QuestionSource(
                            number=2,
                            text="Pregunta de estudio",
                            paragraphs=[3, 4],
                        )
                    ],
                    boxes=[
                        {
                            "title": "Recuadro",
                            "linked_paragraph": 3,
                            "content": ["Texto complementario"],
                            "type": "reflection",
                        }
                    ],
                    transition_allowed=True,
                    summary_allowed=True,
                ),
                GenerationSection(
                    subtitle="ÚLTIMO SUBTÍTULO",
                    paragraphs=[{"number": 5, "text": "Contenido final"}],
                    questions=[
                        QuestionSource(
                            number=3,
                            text="Pregunta final",
                            paragraphs=[5],
                        )
                    ],
                    transition_allowed=True,
                    summary_allowed=False,
                ),
            ],
            review_questions=["Pregunta de repaso"],
        )

        request = build_content_generation_request(plan)

        self.assertEqual(request.article_title, "Título principal")
        self.assertIsNone(request.introduction.subtitle)
        self.assertFalse(request.introduction.needs_transition)
        self.assertFalse(request.introduction.needs_summary)
        self.assertEqual(request.introduction.paragraphs, [introduction_paragraph])
        self.assertEqual(len(request.introduction.questions), 1)
        self.assertEqual(
            request.introduction.questions[0].source_paragraphs,
            [1, 2],
        )

        self.assertEqual(len(request.sections), 2)
        self.assertTrue(request.sections[0].needs_transition)
        self.assertTrue(request.sections[0].needs_summary)
        self.assertTrue(request.sections[1].needs_transition)
        self.assertFalse(request.sections[1].needs_summary)

        question = request.sections[0].questions[0]
        self.assertEqual(question.number, 2)
        self.assertEqual(question.question, "Pregunta de estudio")
        self.assertEqual(question.source_paragraphs, [3, 4])
        self.assertTrue(question.answer_required)
        self.assertTrue(question.application_required)

        box = request.sections[0].boxes[0]
        self.assertEqual(box.title, "Recuadro")
        self.assertEqual(box.linked_paragraph, 3)
        self.assertTrue(box.explanation_required)
        self.assertEqual(request.review_questions, ["Pregunta de repaso"])

        request.introduction.paragraphs[0]["text"] = "Modificado"
        self.assertEqual(introduction_paragraph["text"], "Introducción")

    def test_serializes_request_models(self):
        request = ContentGenerationRequest(
            article_title="Título",
            introduction=SectionGenerationRequest(
                subtitle=None,
                questions=[
                    QuestionGenerationRequest(
                        number=1,
                        question="Pregunta",
                        source_paragraphs=[1],
                    )
                ],
            ),
            sections=[
                SectionGenerationRequest(
                    subtitle="SUBTÍTULO",
                    boxes=[
                        BoxGenerationRequest(
                            title="Recuadro",
                            explanation_required=True,
                            linked_paragraph=2,
                        )
                    ],
                    needs_transition=True,
                )
            ],
            review_questions=["Repaso"],
        )

        data = request.to_dict()

        self.assertEqual(data["article_title"], "Título")
        self.assertEqual(
            data["introduction"]["questions"][0]["source_paragraphs"],
            [1],
        )
        self.assertTrue(data["sections"][0]["boxes"][0]["explanation_required"])
        self.assertEqual(data["review_questions"], ["Repaso"])


if __name__ == "__main__":
    unittest.main()
