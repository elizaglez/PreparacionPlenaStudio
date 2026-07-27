import ast
import inspect
import unittest
from dataclasses import FrozenInstanceError, fields

from app.ai.config import AIProviderConfig
from app.ai.errors import AIProviderConfigurationError


class AIProviderConfigTests(unittest.TestCase):
    def test_stores_valid_provider_settings(self):
        config = AIProviderConfig(
            model="modelo-prueba",
            timeout_seconds=30.0,
            temperature=0.7,
            max_output_tokens=1200,
        )

        self.assertEqual(config.model, "modelo-prueba")
        self.assertEqual(config.timeout_seconds, 30.0)
        self.assertEqual(config.temperature, 0.7)
        self.assertEqual(config.max_output_tokens, 1200)

    def test_is_immutable(self):
        config = AIProviderConfig(
            model="modelo-prueba",
            timeout_seconds=30.0,
        )

        with self.assertRaises(FrozenInstanceError):
            config.model = "otro-modelo"

    def test_rejects_invalid_values(self):
        invalid_values = [
            {"model": "", "timeout_seconds": 30.0},
            {"model": "   ", "timeout_seconds": 30.0},
            {"model": "modelo", "timeout_seconds": 0},
            {"model": "modelo", "timeout_seconds": -1},
            {
                "model": "modelo",
                "timeout_seconds": 30.0,
                "max_output_tokens": 0,
            },
            {
                "model": "modelo",
                "timeout_seconds": 30.0,
                "temperature": -0.1,
            },
            {
                "model": "modelo",
                "timeout_seconds": 30.0,
                "temperature": 2.1,
            },
        ]

        for values in invalid_values:
            with self.subTest(values=values):
                with self.assertRaises(AIProviderConfigurationError):
                    AIProviderConfig(**values)

    def test_contains_no_credentials_or_external_dependencies(self):
        self.assertEqual(
            [field.name for field in fields(AIProviderConfig)],
            [
                "model",
                "timeout_seconds",
                "temperature",
                "max_output_tokens",
            ],
        )

        source = inspect.getsource(inspect.getmodule(AIProviderConfig))
        tree = ast.parse(source)
        imported_modules = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_modules.add(node.module)

        forbidden_modules = {"openai", "requests", "httpx", "app.prompts"}
        self.assertTrue(forbidden_modules.isdisjoint(imported_modules))
        self.assertNotIn("api_key", source.casefold())


if __name__ == "__main__":
    unittest.main()
