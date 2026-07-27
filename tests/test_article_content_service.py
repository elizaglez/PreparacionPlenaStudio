import ast
import inspect
import unittest
from unittest.mock import patch

from app.ai.config import AIProviderConfig
from app.ai.fake_provider import FakeAIProvider
from app.ai.openai_provider import OpenAIProvider
from app.article_content_service import ArticleContentService
from app.generation.article_content_generator import ArticleContentGenerator
from app.generation.content_generation_request import (
    ContentGenerationRequest,
    QuestionGenerationRequest,
    SectionGenerationRequest,
)
from app.generation.generated_article import GeneratedArticle


class ArticleContentServiceTests(unittest.TestCase):
    def setUp(self):
        self.config = AIProviderConfig(
            model="modelo-prueba",
            timeout_seconds=30.0,
            temperature=0.5,
            max_output_tokens=1000,
        )

    def test_composes_fake_provider_and_generates_article(self):
        service = ArticleContentService("fake", self.config)
        request = ContentGenerationRequest(
            article_title="Título",
            introduction=SectionGenerationRequest(
                subtitle=None,
                paragraphs=[{"number": 1, "text": "Contexto"}],
                questions=[
                    QuestionGenerationRequest(
                        number=1,
                        question="Pregunta",
                        source_paragraphs=[1],
                    )
                ],
            ),
        )

        generated = service.generate(request)

        self.assertIsInstance(generated, GeneratedArticle)
        self.assertEqual(generated.title, "Título")
        self.assertEqual(
            generated.introduction.questions[0].answer,
            "Respuesta simulada para prueba",
        )
        self.assertIsInstance(service._generator, ArticleContentGenerator)
        self.assertIsInstance(service._generator._provider, FakeAIProvider)

    def test_accepts_and_uses_injected_provider(self):
        provider = FakeAIProvider()
        service = ArticleContentService(provider)
        request = ContentGenerationRequest(
            article_title="Título inyectado",
            introduction=SectionGenerationRequest(
                subtitle=None,
                paragraphs=[{"number": 1, "text": "Contexto"}],
                questions=[
                    QuestionGenerationRequest(
                        number=1,
                        question="Pregunta",
                        source_paragraphs=[1],
                    )
                ],
            ),
        )

        generated = service.generate(request)

        self.assertIs(service._generator._provider, provider)
        self.assertEqual(generated.title, "Título inyectado")
        self.assertEqual(
            generated.introduction.questions[0].answer,
            "Respuesta simulada para prueba",
        )

    def test_injected_provider_does_not_use_provider_factory(self):
        provider = FakeAIProvider()

        with patch(
            "app.article_content_service.create_provider"
        ) as create_provider_mock:
            service = ArticleContentService(provider)

        create_provider_mock.assert_not_called()
        self.assertIs(service._generator._provider, provider)

    def test_named_provider_still_requires_config(self):
        with self.assertRaisesRegex(TypeError, "config es obligatorio"):
            ArticleContentService("fake")

    def test_composes_openai_provider_with_same_config(self):
        service = ArticleContentService("openai", self.config)

        self.assertIsInstance(service._generator, ArticleContentGenerator)
        provider = service._generator._provider
        self.assertIsInstance(provider, OpenAIProvider)
        self.assertIs(provider.config, self.config)

    def test_service_has_no_concrete_provider_or_external_imports(self):
        source = inspect.getsource(inspect.getmodule(ArticleContentService))
        tree = ast.parse(source)
        imported_modules = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_modules.add(node.module)

        forbidden_modules = {
            "app.ai.fake_provider",
            "app.ai.openai_provider",
            "openai",
            "requests",
            "httpx",
            "app.prompts",
        }
        self.assertTrue(forbidden_modules.isdisjoint(imported_modules))
        lowered_source = source.casefold()
        self.assertNotIn("api_key", lowered_source)
        self.assertNotIn("os.environ", lowered_source)
        self.assertNotIn("getenv", lowered_source)


if __name__ == "__main__":
    unittest.main()
