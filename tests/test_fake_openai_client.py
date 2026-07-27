import ast
import inspect
import unittest

from app.ai.fake_openai_client import FakeOpenAIClient
from app.ai.openai_client_port import OpenAIClientPort


class FakeOpenAIClientTests(unittest.TestCase):
    def test_implements_port_and_returns_deterministic_text(self):
        client = FakeOpenAIClient()

        result = client.generate_text(
            model="modelo-prueba",
            input_text="Contenido",
            temperature=0.5,
            max_output_tokens=1000,
            timeout_seconds=30.0,
        )

        self.assertIsInstance(client, OpenAIClientPort)
        self.assertEqual(result, "Fake AI response")
        self.assertEqual(
            client.calls,
            [
                {
                    "model": "modelo-prueba",
                    "input_text": "Contenido",
                    "temperature": 0.5,
                    "max_output_tokens": 1000,
                    "timeout_seconds": 30.0,
                }
            ],
        )

    def test_accepts_optional_contract_values(self):
        client = FakeOpenAIClient()

        result = client.generate_text(
            model="modelo-prueba",
            input_text="Contenido",
            temperature=None,
            max_output_tokens=None,
            timeout_seconds=1.0,
        )

        self.assertEqual(result, "Fake AI response")
        self.assertIsNone(client.calls[0]["temperature"])
        self.assertIsNone(client.calls[0]["max_output_tokens"])

    def test_has_no_external_dependencies(self):
        source = inspect.getsource(inspect.getmodule(FakeOpenAIClient))
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
