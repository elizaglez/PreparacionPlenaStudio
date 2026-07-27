import inspect
import unittest

from app.generation.article_generation_plan import (
    ArticleGenerationPlan,
    GenerationSection,
    QuestionSource,
)
from app.generation.content_generation_request import ContentGenerationRequest
from app.generation.generated_article import (
    GeneratedArticle,
    GeneratedIntroduction,
)
from app.use_cases.generate_article_content import (
    GenerateArticleContentUseCase,
)


class FakeArticleContentService:
    def __init__(self, result: GeneratedArticle) -> None:
        self.result = result
        self.requests: list[ContentGenerationRequest] = []

    def generate(self, request: ContentGenerationRequest) -> GeneratedArticle:
        self.requests.append(request)
        return self.result


class FakeGeneratedArticleRepository:
    def __init__(self) -> None:
        self.saved: list[GeneratedArticle] = []

    def save(self, article: GeneratedArticle) -> None:
        self.saved.append(article)

    def load(self) -> GeneratedArticle:
        return self.saved[-1]


class GenerateArticleContentUseCaseTests(unittest.TestCase):
    def test_persists_generated_article_when_repository_is_provided(self):
        generated = GeneratedArticle(
            title="Artículo generado",
            introduction=GeneratedIntroduction(),
        )
        service = FakeArticleContentService(generated)
        repository = FakeGeneratedArticleRepository()
        use_case = GenerateArticleContentUseCase(service, repository)
        plan = ArticleGenerationPlan(
            title="Título fuente",
            introduction="Introducción fuente",
        )

        result = use_case.execute(plan)

        self.assertIs(result, generated)
        self.assertEqual(repository.saved, [generated])

    def test_builds_request_calls_service_and_returns_generated_article(self):
        generated = GeneratedArticle(
            title="Artículo generado",
            introduction=GeneratedIntroduction(),
        )
        service = FakeArticleContentService(generated)
        use_case = GenerateArticleContentUseCase(service)
        plan = ArticleGenerationPlan(
            title="Título fuente",
            introduction="Introducción fuente",
            sections=[
                GenerationSection(
                    subtitle=None,
                    paragraphs=[{"number": 1, "text": "Párrafo inicial"}],
                    questions=[
                        QuestionSource(
                            number=1,
                            text="¿Pregunta introductoria?",
                            paragraphs=[1],
                        )
                    ],
                ),
                GenerationSection(
                    subtitle="SUBTÍTULO",
                    paragraphs=[{"number": 2, "text": "Párrafo fuente"}],
                    questions=[
                        QuestionSource(
                            number=2,
                            text="¿Pregunta principal?",
                            paragraphs=[2],
                        )
                    ],
                    transition_allowed=True,
                    summary_allowed=True,
                ),
            ],
            review_questions=["¿Pregunta de repaso?"],
        )

        result = use_case.execute(plan)

        self.assertIs(result, generated)
        self.assertEqual(len(service.requests), 1)
        request = service.requests[0]
        self.assertIsInstance(request, ContentGenerationRequest)
        self.assertEqual(request.article_title, "Título fuente")
        self.assertEqual(len(request.introduction.questions), 1)
        self.assertEqual(request.introduction.questions[0].number, 1)
        self.assertEqual(len(request.sections), 1)
        self.assertEqual(request.sections[0].subtitle, "SUBTÍTULO")
        self.assertEqual(request.sections[0].questions[0].source_paragraphs, [2])
        self.assertTrue(request.sections[0].needs_transition)
        self.assertTrue(request.sections[0].needs_summary)
        self.assertEqual(request.review_questions, ["¿Pregunta de repaso?"])

    def test_has_no_openai_sdk_or_prompt_dependencies(self):
        module = inspect.getmodule(GenerateArticleContentUseCase)
        self.assertIsNotNone(module)
        source = inspect.getsource(module)

        self.assertNotIn("OpenAI", source)
        self.assertNotIn("openai", source)
        self.assertNotIn("Prompt", source)
        self.assertNotIn("prompt", source)
        self.assertNotIn("create_provider", source)
        self.assertNotIn("get_secret", source)


if __name__ == "__main__":
    unittest.main()
