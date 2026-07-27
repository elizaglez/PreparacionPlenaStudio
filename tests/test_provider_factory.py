import ast
import inspect
import unittest

from app.ai.config import AIProviderConfig
from app.ai.errors import AIProviderConfigurationError
from app.ai.fake_provider import FakeAIProvider
from app.ai.openai_provider import OpenAIProvider
from app.ai.provider import AIProvider
from app.ai.provider_factory import create_provider


class AIProviderFactoryTests(unittest.TestCase):
    def setUp(self):
        self.config = AIProviderConfig(
            model="modelo-prueba",
            timeout_seconds=30.0,
            temperature=0.5,
            max_output_tokens=1000,
        )

    def test_creates_fake_provider(self):
        provider = create_provider("fake", self.config)

        self.assertIsInstance(provider, AIProvider)
        self.assertIsInstance(provider, FakeAIProvider)

    def test_creates_openai_provider_with_same_config(self):
        provider = create_provider("openai", self.config)

        self.assertIsInstance(provider, AIProvider)
        self.assertIsInstance(provider, OpenAIProvider)
        self.assertIs(provider.config, self.config)

    def test_normalizes_provider_name(self):
        self.assertIsInstance(
            create_provider("  FAKE  ", self.config),
            FakeAIProvider,
        )
        self.assertIsInstance(
            create_provider("  OpenAI  ", self.config),
            OpenAIProvider,
        )

    def test_rejects_unknown_provider(self):
        with self.assertRaises(AIProviderConfigurationError):
            create_provider("desconocido", self.config)

    def test_has_no_external_dependencies(self):
        source = inspect.getsource(inspect.getmodule(create_provider))
        tree = ast.parse(source)
        imported_modules = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_modules.add(node.module)

        forbidden_modules = {"openai", "requests", "httpx", "app.prompts"}
        self.assertTrue(forbidden_modules.isdisjoint(imported_modules))
        lowered_source = source.casefold()
        self.assertNotIn("api_key", lowered_source)
        self.assertNotIn("os.environ", lowered_source)
        self.assertNotIn("getenv", lowered_source)


if __name__ == "__main__":
    unittest.main()
