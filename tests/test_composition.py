import ast
import inspect
import sys
import unittest

from app.ai.config import AIProviderConfig
from app.article_content_service import ArticleContentService
from app.composition import create_article_content_service
from app.generation.content_generation_request import (
    ContentGenerationRequest,
    QuestionGenerationRequest,
    SectionGenerationRequest,
)
from app.generation.generated_article import GeneratedArticle


class CompositionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = AIProviderConfig(
            model="modelo-prueba",
            timeout_seconds=30.0,
            temperature=0.5,
            max_output_tokens=1000,
        )

    def test_creates_article_content_service(self):
        service = create_article_content_service("fake", self.config)

        self.assertIsInstance(service, ArticleContentService)

    def test_composed_fake_provider_generates_article(self):
        service = create_article_content_service("fake", self.config)
        request = ContentGenerationRequest(
            article_title="Título de prueba",
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
        self.assertEqual(generated.title, "Título de prueba")
        self.assertEqual(
            generated.introduction.questions[0].answer,
            "Respuesta simulada para prueba",
        )

    def test_composition_has_no_sdk_prompt_or_secret_dependencies(self):
        source = inspect.getsource(
            inspect.getmodule(create_article_content_service)
        )
        tree = ast.parse(source)
        imported_modules = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_modules.add(node.module)

        forbidden_modules = {
            "openai",
            "requests",
            "httpx",
            "os",
            "app.prompts",
            "app.ai.fake_provider",
            "app.ai.openai_provider",
        }
        self.assertTrue(forbidden_modules.isdisjoint(imported_modules))
        self.assertNotIn("openai", sys.modules)
        lowered_source = source.casefold()
        self.assertNotIn("api_key", lowered_source)
        self.assertNotIn("environ", lowered_source)
        self.assertNotIn("getenv", lowered_source)
        self.assertNotIn("secret", lowered_source)


if __name__ == "__main__":
    unittest.main()
