import ast
import inspect
import unittest

from app.ai.errors import (
    AIProviderConfigurationError,
    AIProviderError,
    AIProviderPermanentError,
    AIProviderResponseError,
    AIProviderTemporaryError,
)


class AIProviderErrorTests(unittest.TestCase):
    def test_error_hierarchy(self):
        self.assertTrue(issubclass(AIProviderTemporaryError, AIProviderError))
        self.assertTrue(issubclass(AIProviderPermanentError, AIProviderError))
        self.assertTrue(
            issubclass(AIProviderConfigurationError, AIProviderPermanentError)
        )
        self.assertTrue(issubclass(AIProviderResponseError, AIProviderPermanentError))
        self.assertFalse(issubclass(AIProviderTemporaryError, AIProviderPermanentError))

    def test_errors_can_be_raised_and_caught_by_base_type(self):
        errors = [
            AIProviderTemporaryError("timeout"),
            AIProviderPermanentError("operación no soportada"),
            AIProviderConfigurationError("configuración inválida"),
            AIProviderResponseError("respuesta inválida"),
        ]

        for error in errors:
            with self.subTest(error=type(error).__name__):
                with self.assertRaises(AIProviderError) as caught:
                    raise error
                self.assertIs(caught.exception, error)

    def test_has_no_external_dependencies(self):
        source = inspect.getsource(inspect.getmodule(AIProviderError))
        tree = ast.parse(source)
        imports = [
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
        ]

        self.assertEqual(imports, [])
        self.assertNotIn("API_KEY", source)
        self.assertNotIn("api_key", source)
        self.assertNotIn("PromptLoader", source)


if __name__ == "__main__":
    unittest.main()
