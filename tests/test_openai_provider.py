import ast
import inspect
import unittest

from app.ai.errors import AIProviderConfigurationError, AIProviderError
from app.ai.openai_provider import OpenAIProvider
from app.ai.provider import AIProvider


class OpenAIProviderTests(unittest.TestCase):
    def test_implements_complete_provider_contract(self):
        self.assertTrue(issubclass(OpenAIProvider, AIProvider))
        self.assertFalse(inspect.isabstract(OpenAIProvider))
        provider = OpenAIProvider()

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
