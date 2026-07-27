import ast
import inspect
import unittest
from unittest.mock import Mock, patch

from app.ai.errors import AIProviderConfigurationError
from app.ai.openai_client_adapter import OpenAIClientAdapter
from app.ai.openai_client_factory import create_openai_client
from app.ai.openai_client_port import OpenAIClientPort


class OpenAIClientFactoryTests(unittest.TestCase):
    def test_creates_client_port_with_received_api_key(self):
        adapter = Mock(spec=OpenAIClientPort)

        with patch.object(
            OpenAIClientAdapter,
            "from_api_key",
            return_value=adapter,
        ) as factory:
            result = create_openai_client("clave-de-prueba")

        factory.assert_called_once_with("clave-de-prueba")
        self.assertIs(result, adapter)

    def test_rejects_empty_api_key(self):
        for api_key in (None, "", "   ", 42):
            with self.subTest(api_key=api_key):
                with self.assertRaises(AIProviderConfigurationError):
                    create_openai_client(api_key)

    def test_factory_does_not_read_environment_or_import_sdk(self):
        source = inspect.getsource(inspect.getmodule(create_openai_client))
        tree = ast.parse(source)
        imported_modules = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_modules.add(node.module)

        forbidden_modules = {"openai", "requests", "httpx", "os"}
        self.assertTrue(forbidden_modules.isdisjoint(imported_modules))
        lowered_source = source.casefold()
        self.assertNotIn("environ", lowered_source)
        self.assertNotIn("getenv", lowered_source)
        self.assertNotIn("openai_api_key", lowered_source)


if __name__ == "__main__":
    unittest.main()
