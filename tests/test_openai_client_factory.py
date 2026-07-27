import ast
import inspect
import unittest

from app.ai.openai_client_adapter import OpenAIClientAdapter
from app.ai.openai_client_factory import create_openai_client
from app.ai.openai_client_port import OpenAIClientPort


class SimulatedClient:
    def __init__(self) -> None:
        self.calls = []

    def generate_text(
        self,
        *,
        model: str,
        input_text: str,
        temperature: float | None,
        max_output_tokens: int | None,
        timeout_seconds: float,
    ) -> str:
        self.calls.append(
            {
                "model": model,
                "input_text": input_text,
                "temperature": temperature,
                "max_output_tokens": max_output_tokens,
                "timeout_seconds": timeout_seconds,
            }
        )
        return "Respuesta del cliente simulado"


class OpenAIClientFactoryTests(unittest.TestCase):
    def test_creates_client_port_through_adapter(self):
        internal_client = SimulatedClient()

        client = create_openai_client(internal_client)

        self.assertIsInstance(client, OpenAIClientPort)
        self.assertIsInstance(client, OpenAIClientAdapter)
        self.assertIs(client.client, internal_client)

    def test_created_port_delegates_to_replaceable_client(self):
        internal_client = SimulatedClient()
        client = create_openai_client(internal_client)

        result = client.generate_text(
            model="modelo-prueba",
            input_text="Entrada",
            temperature=None,
            max_output_tokens=500,
            timeout_seconds=15.0,
        )

        self.assertEqual(result, "Respuesta del cliente simulado")
        self.assertEqual(
            internal_client.calls,
            [
                {
                    "model": "modelo-prueba",
                    "input_text": "Entrada",
                    "temperature": None,
                    "max_output_tokens": 500,
                    "timeout_seconds": 15.0,
                }
            ],
        )

    def test_has_no_sdk_environment_or_secret_dependencies(self):
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
        self.assertNotIn("api_key", lowered_source)
        self.assertNotIn("environ", lowered_source)
        self.assertNotIn("getenv", lowered_source)
        self.assertNotIn("secret", lowered_source)


if __name__ == "__main__":
    unittest.main()
