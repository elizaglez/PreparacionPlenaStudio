import ast
import inspect
import subprocess
import sys
import unittest

from app.ai.config import AIProviderConfig
from app.ai.errors import AIProviderConfigurationError
from app.ai.fake_openai_client import FakeOpenAIClient
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
        from app.ai.fake_provider import FakeAIProvider

        self.assertIsInstance(provider, AIProvider)
        self.assertIsInstance(provider, FakeAIProvider)

    def test_creates_openai_provider_with_same_config(self):
        provider = create_provider("openai", self.config)
        from app.ai.openai_provider import OpenAIProvider

        self.assertIsInstance(provider, AIProvider)
        self.assertIsInstance(provider, OpenAIProvider)
        self.assertIs(provider.config, self.config)

    def test_passes_external_client_to_openai_provider(self):
        client = FakeOpenAIClient()

        provider = create_provider(
            "openai",
            self.config,
            openai_client=client,
        )

        self.assertIs(provider.client, client)

    def test_fake_provider_does_not_use_openai_client(self):
        client = FakeOpenAIClient()

        provider = create_provider(
            "fake",
            self.config,
            openai_client=client,
        )
        from app.ai.fake_provider import FakeAIProvider

        self.assertIsInstance(provider, FakeAIProvider)
        self.assertFalse(client.calls)

    def test_normalizes_provider_name(self):
        from app.ai.fake_provider import FakeAIProvider
        from app.ai.openai_provider import OpenAIProvider

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

    def test_import_does_not_load_concrete_providers(self):
        output = subprocess.check_output(
            [
                sys.executable,
                "-c",
                (
                    "import sys; import app.ai.provider_factory; "
                    "print('app.ai.fake_provider' in sys.modules); "
                    "print('app.ai.openai_provider' in sys.modules)"
                ),
            ],
            text=True,
        )

        self.assertEqual(output.splitlines(), ["False", "False"])

    def test_loads_only_selected_concrete_provider(self):
        script = (
            "import sys; "
            "from app.ai.config import AIProviderConfig; "
            "from app.ai.provider_factory import create_provider; "
            "config = AIProviderConfig(model='test', timeout_seconds=1); "
            "create_provider({provider_name!r}, config); "
            "print('app.ai.fake_provider' in sys.modules); "
            "print('app.ai.openai_provider' in sys.modules)"
        )
        expectations = {
            "fake": ["True", "False"],
            "openai": ["False", "True"],
        }

        for provider_name, expected in expectations.items():
            with self.subTest(provider_name=provider_name):
                output = subprocess.check_output(
                    [
                        sys.executable,
                        "-c",
                        script.format(provider_name=provider_name),
                    ],
                    text=True,
                )
                self.assertEqual(output.splitlines(), expected)

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
