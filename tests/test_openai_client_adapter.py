import ast
import inspect
import unittest

from app.ai.openai_client_adapter import OpenAIClientAdapter
from app.ai.openai_client_port import OpenAIClientPort


class SimulatedInternalClient:
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
        return "Respuesta delegada"


class OpenAIClientAdapterTests(unittest.TestCase):
    def test_implements_port_and_preserves_internal_client(self):
        internal_client = SimulatedInternalClient()
        adapter = OpenAIClientAdapter(internal_client)

        self.assertIsInstance(adapter, OpenAIClientPort)
        self.assertIs(adapter.client, internal_client)

    def test_delegates_generate_text_with_complete_contract(self):
        internal_client = SimulatedInternalClient()
        adapter = OpenAIClientAdapter(internal_client)

        result = adapter.generate_text(
            model="modelo-prueba",
            input_text="Contenido para generar",
            temperature=0.4,
            max_output_tokens=800,
            timeout_seconds=25.0,
        )

        self.assertEqual(result, "Respuesta delegada")
        self.assertEqual(
            internal_client.calls,
            [
                {
                    "model": "modelo-prueba",
                    "input_text": "Contenido para generar",
                    "temperature": 0.4,
                    "max_output_tokens": 800,
                    "timeout_seconds": 25.0,
                }
            ],
        )

    def test_accepts_optional_generation_values(self):
        internal_client = SimulatedInternalClient()
        adapter = OpenAIClientAdapter(internal_client)

        adapter.generate_text(
            model="modelo-prueba",
            input_text="Contenido",
            temperature=None,
            max_output_tokens=None,
            timeout_seconds=1.0,
        )

        self.assertIsNone(internal_client.calls[0]["temperature"])
        self.assertIsNone(internal_client.calls[0]["max_output_tokens"])

    def test_has_no_external_dependencies(self):
        source = inspect.getsource(inspect.getmodule(OpenAIClientAdapter))
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
