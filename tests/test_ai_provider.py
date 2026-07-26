import inspect
import unittest

from app.ai.fake_provider import FakeAIProvider
from app.ai.provider import AIProvider


class AIProviderTests(unittest.TestCase):
    def test_ai_provider_defines_abstract_contract(self):
        self.assertTrue(inspect.isabstract(AIProvider))
        self.assertEqual(
            AIProvider.__abstractmethods__,
            {
                "generate_answer",
                "generate_application",
                "generate_summary",
                "generate_heygen_transition",
            },
        )
        with self.assertRaises(TypeError):
            AIProvider()

    def test_fake_provider_implements_all_operations(self):
        self.assertTrue(issubclass(FakeAIProvider, AIProvider))
        provider = FakeAIProvider()

        self.assertEqual(
            provider.generate_answer(
                "¿Qué aprendemos?",
                ["Párrafo uno", "Párrafo dos"],
            ),
            "Respuesta simulada para prueba",
        )
        self.assertEqual(
            provider.generate_application("Respuesta"),
            "Aplicación simulada para prueba",
        )
        self.assertEqual(
            provider.generate_summary("Contenido de la sección"),
            "Resumen simulado para prueba",
        )
        self.assertEqual(
            provider.generate_heygen_transition("SUBTÍTULO"),
            "Transición HeyGen simulada para prueba",
        )


if __name__ == "__main__":
    unittest.main()
