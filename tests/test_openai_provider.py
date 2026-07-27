import ast
import inspect
import unittest

from app.ai.config import AIProviderConfig
from app.ai.errors import AIProviderConfigurationError, AIProviderError
from app.ai.fake_openai_client import FakeOpenAIClient
from app.ai.openai_client_port import OpenAIClientPort
from app.ai.openai_provider import OpenAIProvider
from app.ai.provider import AIProvider
from app.generation.article_content_generator import ArticleContentGenerator


class OpenAIProviderTests(unittest.TestCase):
    def test_implements_complete_provider_contract(self):
        self.assertTrue(issubclass(OpenAIProvider, AIProvider))
        self.assertFalse(inspect.isabstract(OpenAIProvider))
        config = AIProviderConfig(
            model="modelo-prueba",
            timeout_seconds=30.0,
            temperature=0.5,
            max_output_tokens=1000,
        )
        client = FakeOpenAIClient()
        provider = OpenAIProvider(config, client)

        self.assertIs(provider.config, config)
        self.assertIs(provider.client, client)
        self.assertIsInstance(client, OpenAIClientPort)
        self.assertIsInstance(
            ArticleContentGenerator(provider),
            ArticleContentGenerator,
        )

        results = [
            provider.generate_answer("Pregunta", ["Contexto 1", "Contexto 2"]),
            provider.generate_application("Respuesta"),
            provider.generate_summary("Contenido de sección"),
            provider.generate_box_explanation("Contenido de recuadro"),
            provider.generate_heygen_transition("SUBTÍTULO"),
        ]

        self.assertEqual(results, ["Fake AI response"] * 5)
        self.assertEqual(
            [call["input_text"] for call in client.calls],
            [
                "Pregunta\n\nContexto 1\n\nContexto 2",
                "Respuesta",
                "Contenido de sección",
                "Contenido de recuadro",
                "SUBTÍTULO",
            ],
        )
        for call in client.calls:
            self.assertEqual(call["model"], "modelo-prueba")
            self.assertEqual(call["temperature"], 0.5)
            self.assertEqual(call["max_output_tokens"], 1000)
            self.assertEqual(call["timeout_seconds"], 30.0)

    def test_operations_require_injected_client(self):
        config = AIProviderConfig(
            model="modelo-prueba",
            timeout_seconds=30.0,
        )
        provider = OpenAIProvider(config)
        operations = [
            lambda: provider.generate_answer("Pregunta", ["Contexto"]),
            lambda: provider.generate_application("Respuesta"),
            lambda: provider.generate_summary("Contenido de sección"),
            lambda: provider.generate_box_explanation("Contenido de recuadro"),
            lambda: provider.generate_heygen_transition("SUBTÍTULO"),
        ]

        for operation in operations:
            with self.subTest(operation=operation):
                with self.assertRaises(AIProviderError) as caught:
                    operation()
                self.assertIsInstance(
                    caught.exception,
                    AIProviderConfigurationError,
                )

    def test_accepts_missing_client_without_creating_one(self):
        config = AIProviderConfig(
            model="modelo-prueba",
            timeout_seconds=30.0,
        )

        provider = OpenAIProvider(config)

        self.assertIs(provider.config, config)
        self.assertIsNone(provider.client)

    def test_has_no_external_ai_or_prompt_dependencies(self):
        source = inspect.getsource(inspect.getmodule(OpenAIProvider))
        tree = ast.parse(source)
        imported_modules = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_modules.add(node.module)

        forbidden_modules = {"openai", "requests", "httpx", "app.prompts"}
        self.assertTrue(forbidden_modules.isdisjoint(imported_modules))
        self.assertNotIn("API_KEY", source)
        self.assertNotIn("api_key", source)


if __name__ == "__main__":
    unittest.main()
