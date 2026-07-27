import unittest
from unittest.mock import patch

from app.ai.config import AIProviderConfig
from app.ai.fake_openai_client import FakeOpenAIClient
from app.ai.openai_client_adapter import OpenAIClientAdapter
from app.ai.openai_provider import OpenAIProvider
from app.article_content_service import ArticleContentService
from app.composition import create_article_content_service
from app.generation.article_content_generator import ArticleContentGenerator
from app.generation.content_generation_request import (
    ContentGenerationRequest,
    QuestionGenerationRequest,
    SectionGenerationRequest,
)
from app.generation.generated_article import GeneratedArticle
from app.security.secret_loader import SecretLoader


class AICompositionSmokeTests(unittest.TestCase):
    def test_full_composition_uses_controlled_client_without_real_api(self):
        secret_loader = SecretLoader(
            lambda name: (
                "clave-simulada-no-real"
                if name == "OPENAI_API_KEY"
                else None
            )
        )
        api_key = secret_loader.get_secret("OPENAI_API_KEY")
        config = AIProviderConfig(
            model="modelo-controlado",
            timeout_seconds=5.0,
            temperature=0.2,
            max_output_tokens=200,
        )
        controlled_client = FakeOpenAIClient()

        with patch.object(
            OpenAIClientAdapter,
            "from_api_key",
            return_value=controlled_client,
        ) as sdk_client_factory:
            service = create_article_content_service(
                "openai",
                config,
                openai_api_key=api_key,
            )

        request = ContentGenerationRequest(
            article_title="Artículo de smoke test",
            introduction=SectionGenerationRequest(
                subtitle=None,
                paragraphs=[
                    {"number": 1, "text": "Contexto controlado"}
                ],
                questions=[
                    QuestionGenerationRequest(
                        number=1,
                        question="¿Pregunta controlada?",
                        source_paragraphs=[1],
                    )
                ],
            ),
        )

        generated = service.generate(request)

        sdk_client_factory.assert_called_once_with("clave-simulada-no-real")
        self.assertIsInstance(service, ArticleContentService)
        self.assertIsInstance(service._generator, ArticleContentGenerator)
        provider = service._generator._provider
        self.assertIsInstance(provider, OpenAIProvider)
        self.assertIs(provider.client, controlled_client)
        self.assertIsInstance(generated, GeneratedArticle)
        self.assertEqual(generated.title, "Artículo de smoke test")
        self.assertEqual(
            generated.introduction.questions[0].answer,
            "Fake AI response",
        )
        self.assertEqual(
            generated.introduction.questions[0].application,
            "Fake AI response",
        )
        self.assertEqual(len(controlled_client.calls), 2)
        self.assertEqual(
            controlled_client.calls[0],
            {
                "model": "modelo-controlado",
                "input_text": (
                    "¿Pregunta controlada?\n\nContexto controlado"
                ),
                "temperature": 0.2,
                "max_output_tokens": 200,
                "timeout_seconds": 5.0,
            },
        )


if __name__ == "__main__":
    unittest.main()
