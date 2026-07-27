import ast
import inspect
import unittest

from app.security.secret_loader import SecretLoader, SecretNotFoundError


class SecretLoaderTests(unittest.TestCase):
    def test_gets_secret_from_simulated_external_source(self):
        requested_names = []

        def source(name):
            requested_names.append(name)
            return {"SERVICE_TOKEN": "  valor-simulado  "}.get(name)

        loader = SecretLoader(source)

        result = loader.get_secret(" SERVICE_TOKEN ")

        self.assertEqual(result, "valor-simulado")
        self.assertEqual(requested_names, ["SERVICE_TOKEN"])

    def test_does_not_cache_or_expose_secret_value(self):
        values = iter(["primer-valor", "segundo-valor"])
        source = lambda _name: next(values)
        loader = SecretLoader(source)

        first = loader.get_secret("TOKEN")
        second = loader.get_secret("TOKEN")

        self.assertEqual(first, "primer-valor")
        self.assertEqual(second, "segundo-valor")
        self.assertEqual(vars(loader), {"_source": source})
        self.assertNotIn(first, repr(loader))
        self.assertNotIn(second, repr(loader))

    def test_missing_secret_raises_clear_error_without_value(self):
        loader = SecretLoader(lambda _name: None)

        with self.assertRaises(SecretNotFoundError) as raised:
            loader.get_secret("MISSING_TOKEN")

        message = str(raised.exception)
        self.assertIn("MISSING_TOKEN", message)
        self.assertNotIn("None", message)

    def test_rejects_blank_secret_name(self):
        loader = SecretLoader(lambda _name: "valor")

        for name in (None, "", "   "):
            with self.subTest(name=name):
                with self.assertRaises(SecretNotFoundError):
                    loader.get_secret(name)

    def test_has_no_openai_http_or_logging_dependencies(self):
        source = inspect.getsource(inspect.getmodule(SecretLoader))
        tree = ast.parse(source)
        imported_modules = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_modules.add(node.module)

        forbidden_modules = {
            "openai",
            "requests",
            "httpx",
            "logging",
            "app.ai",
        }
        self.assertTrue(forbidden_modules.isdisjoint(imported_modules))
        lowered_source = source.casefold()
        self.assertNotIn("print(", lowered_source)
        self.assertNotIn("api_key", lowered_source)


if __name__ == "__main__":
    unittest.main()
