import unittest

from app.ai.fake_provider import FakeAIProvider
from app.generation.article_content_generator import ArticleContentGenerator
from app.generation.content_generation_request import (
    BoxGenerationRequest,
    ContentGenerationRequest,
    QuestionGenerationRequest,
    SectionGenerationRequest,
)


class ArticleContentGeneratorTests(unittest.TestCase):
    def test_generates_article_content_through_provider(self):
        request = ContentGenerationRequest(
            article_title="Título principal",
            introduction=SectionGenerationRequest(
                subtitle=None,
                paragraphs=[
                    {"number": 1, "text": "Párrafo introductorio"},
                ],
                questions=[
                    QuestionGenerationRequest(
                        number=1,
                        question="Pregunta introductoria",
                        source_paragraphs=[1],
                    )
                ],
            ),
            sections=[
                SectionGenerationRequest(
                    subtitle="PRIMER SUBTÍTULO",
                    paragraphs=[
                        {"number": 2, "text": "Contenido de la sección"},
                    ],
                    questions=[
                        QuestionGenerationRequest(
                            number=2,
                            question="Pregunta de estudio",
                            source_paragraphs=[2],
                        )
                    ],
                    boxes=[
                        BoxGenerationRequest(
                            title="Recuadro complementario",
                            explanation_required=True,
                            linked_paragraph=2,
                        )
                    ],
                    needs_transition=True,
                    needs_summary=True,
                )
            ],
            review_questions=["Pregunta de repaso"],
        )

        generated = ArticleContentGenerator(FakeAIProvider()).generate(request)

        self.assertEqual(generated.title, "Título principal")
        self.assertEqual(
            generated.introduction.paragraphs,
            [{"number": 1, "text": "Párrafo introductorio"}],
        )
        self.assertEqual(len(generated.introduction.questions), 1)
        introduction_question = generated.introduction.questions[0]
        self.assertEqual(
            introduction_question.answer,
            "Respuesta simulada para prueba",
        )
        self.assertEqual(
            introduction_question.application,
            "Aplicación simulada para prueba",
        )

        self.assertEqual(len(generated.sections), 1)
        section = generated.sections[0]
        self.assertEqual(section.subtitle, "PRIMER SUBTÍTULO")
        self.assertEqual(
            section.heygen_transition,
            "Transición HeyGen simulada para prueba",
        )
        self.assertEqual(
            section.questions[0].answer,
            "Respuesta simulada para prueba",
        )
        self.assertEqual(
            section.questions[0].application,
            "Aplicación simulada para prueba",
        )
        self.assertEqual(section.section_summary, "Resumen simulado para prueba")

        self.assertEqual(len(section.boxes), 1)
        box = section.boxes[0]
        self.assertEqual(box.title, "Recuadro complementario")
        self.assertEqual(box.linked_paragraph, 2)
        self.assertEqual(box.explanation, "Resumen simulado para prueba")
        self.assertEqual(generated.review_questions, ["Pregunta de repaso"])

    def test_respects_disabled_generation_flags(self):
        request = ContentGenerationRequest(
            article_title="Título",
            introduction=SectionGenerationRequest(subtitle=None),
            sections=[
                SectionGenerationRequest(
                    subtitle="ÚLTIMO SUBTÍTULO",
                    questions=[
                        QuestionGenerationRequest(
                            number=1,
                            question="Pregunta",
                            answer_required=False,
                            application_required=False,
                        )
                    ],
                    boxes=[
                        BoxGenerationRequest(
                            title="Recuadro",
                            explanation_required=False,
                            linked_paragraph=1,
                        )
                    ],
                    needs_transition=False,
                    needs_summary=False,
                )
            ],
        )

        generated = ArticleContentGenerator(FakeAIProvider()).generate(request)

        section = generated.sections[0]
        self.assertIsNone(section.heygen_transition)
        self.assertIsNone(section.section_summary)
        self.assertEqual(section.questions[0].answer, "")
        self.assertEqual(section.questions[0].application, "")
        self.assertEqual(section.boxes[0].explanation, "")


if __name__ == "__main__":
    unittest.main()
