import ast
import inspect
import subprocess
import sys
import unittest
from unittest.mock import patch

from app.ai.config import AIProviderConfig
from app.ai.errors import AIProviderConfigurationError
from app.ai.fake_openai_client import FakeOpenAIClient
from app.ai.openai_provider import OpenAIProvider
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

    def test_composes_openai_provider_with_external_fake_client(self):
        fake_client = FakeOpenAIClient()

        service = create_article_content_service(
            "openai",
            self.config,
            openai_client=fake_client,
        )

        provider = service._generator._provider
        self.assertIsInstance(provider, OpenAIProvider)
        self.assertIs(provider.config, self.config)
        self.assertIs(provider.client, fake_client)

    def test_composes_real_client_port_from_explicit_api_key(self):
        fake_client = FakeOpenAIClient()

        with patch(
            "app.composition.create_openai_client",
            return_value=fake_client,
        ) as client_factory:
            service = create_article_content_service(
                "openai",
                self.config,
                openai_api_key="clave-de-prueba",
            )

        client_factory.assert_called_once_with("clave-de-prueba")
        self.assertIs(service._generator._provider.client, fake_client)

    def test_fake_provider_never_creates_openai_client(self):
        with patch(
            "app.composition.create_openai_client"
        ) as client_factory:
            service = create_article_content_service(
                "  FAKE  ",
                self.config,
                openai_api_key="clave-que-debe-ignorarse",
            )

        client_factory.assert_not_called()
        self.assertIsInstance(service, ArticleContentService)

    def test_rejects_client_and_api_key_together(self):
        with self.assertRaises(AIProviderConfigurationError):
            create_article_content_service(
                "openai",
                self.config,
                openai_client=FakeOpenAIClient(),
                openai_api_key="clave-de-prueba",
            )

    def test_composed_openai_service_generates_through_fake_client(self):
        fake_client = FakeOpenAIClient()
        service = create_article_content_service(
            "openai",
            self.config,
            openai_client=fake_client,
        )
        request = ContentGenerationRequest(
            article_title="Artículo OpenAI simulado",
            introduction=SectionGenerationRequest(
                subtitle=None,
                paragraphs=[{"number": 1, "text": "Contexto fuente"}],
                questions=[
                    QuestionGenerationRequest(
                        number=1,
                        question="Pregunta de prueba",
                        source_paragraphs=[1],
                    )
                ],
            ),
        )

        generated = service.generate(request)

        self.assertEqual(generated.title, "Artículo OpenAI simulado")
        self.assertEqual(
            generated.introduction.questions[0].answer,
            "Fake AI response",
        )
        self.assertEqual(
            generated.introduction.questions[0].application,
            "Fake AI response",
        )
        self.assertEqual(len(fake_client.calls), 2)
        self.assertEqual(
            fake_client.calls[0],
            {
                "model": "modelo-prueba",
                "input_text": "Pregunta de prueba\n\nContexto fuente",
                "temperature": 0.5,
                "max_output_tokens": 1000,
                "timeout_seconds": 30.0,
            },
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
        output = subprocess.check_output(
            [
                sys.executable,
                "-c",
                (
                    "import sys; import app.composition; "
                    "print('openai' in sys.modules)"
                ),
            ],
            text=True,
        )
        self.assertEqual(output.strip(), "False")
        lowered_source = source.casefold()
        self.assertNotIn("environ", lowered_source)
        self.assertNotIn("getenv", lowered_source)
        self.assertNotIn("secret", lowered_source)


if __name__ == "__main__":
    unittest.main()
