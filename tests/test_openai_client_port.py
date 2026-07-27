import ast
import inspect
import unittest

from app.ai.openai_client_port import OpenAIClientPort


class FakeOpenAIClient:
    def __init__(self):
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
        return "Texto simulado"


class OpenAIClientPortTests(unittest.TestCase):
    def test_fake_client_implements_port_and_accepts_interface(self):
        client = FakeOpenAIClient()

        result = client.generate_text(
            model="modelo-prueba",
            input_text="Entrada",
            temperature=0.5,
            max_output_tokens=1000,
            timeout_seconds=30.0,
        )

        self.assertIsInstance(client, OpenAIClientPort)
        self.assertEqual(result, "Texto simulado")
        self.assertEqual(
            client.calls,
            [
                {
                    "model": "modelo-prueba",
                    "input_text": "Entrada",
                    "temperature": 0.5,
                    "max_output_tokens": 1000,
                    "timeout_seconds": 30.0,
                }
            ],
        )

    def test_port_has_small_keyword_only_interface(self):
        signature = inspect.signature(OpenAIClientPort.generate_text)

        self.assertEqual(
            list(signature.parameters),
            [
                "self",
                "model",
                "input_text",
                "temperature",
                "max_output_tokens",
                "timeout_seconds",
            ],
        )
        for name in list(signature.parameters)[1:]:
            self.assertEqual(
                signature.parameters[name].kind,
                inspect.Parameter.KEYWORD_ONLY,
            )

    def test_has_no_external_dependencies(self):
        source = inspect.getsource(inspect.getmodule(OpenAIClientPort))
        tree = ast.parse(source)
        imported_modules = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_modules.add(node.module)

        self.assertEqual(imported_modules, {"__future__", "typing"})
        lowered_source = source.casefold()
        self.assertNotIn("api_key", lowered_source)
        self.assertNotIn("os.environ", lowered_source)
        self.assertNotIn("getenv", lowered_source)


if __name__ == "__main__":
    unittest.main()
