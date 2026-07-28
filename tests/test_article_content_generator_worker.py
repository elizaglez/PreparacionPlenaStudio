import subprocess
import sys
import tempfile
import unittest

from app.ai.config import AIProviderConfig
from app.ai.errors import (
    AIProviderConfigurationError,
    AIProviderResponseError,
    AIProviderTemporaryError,
)
from app.article_content_generator_worker import ArticleContentGeneratorWorker
from app.generation.article_generation_plan import (
    ArticleGenerationPlan,
    GenerationSection,
    QuestionSource,
)
from app.generation.generated_article import GeneratedArticle
from app.persistence.generated_article_repository import (
    JsonGeneratedArticleRepository,
)
from app.security.secret_loader import SecretNotFoundError


class ArticleContentGeneratorWorkerTests(unittest.TestCase):
    def setUp(self):
        self.plan = ArticleGenerationPlan(
            title="Título de prueba",
            introduction="Introducción",
            sections=[
                GenerationSection(
                    subtitle=None,
                    paragraphs=[{"number": 1, "text": "Párrafo fuente"}],
                    questions=[
                        QuestionSource(
                            number=1,
                            text="¿Pregunta de prueba?",
                            paragraphs=[1],
                        )
                    ],
                )
            ],
        )
        self.config = AIProviderConfig(
            model="modelo-prueba",
            timeout_seconds=30,
        )

    def test_generates_and_persists_with_fake_provider(self):
        with tempfile.TemporaryDirectory() as temporary:
            worker = ArticleContentGeneratorWorker(
                self.plan,
                "fake",
                self.config,
                temporary,
            )
            progress = []
            results = []
            errors = []
            worker.progress.connect(
                lambda value, message: progress.append((value, message))
            )
            worker.finished.connect(results.append)
            worker.failed.connect(errors.append)

            worker.run()

            self.assertEqual(errors, [])
            self.assertEqual([value for value, _ in progress], [0, 10, 100])
            self.assertEqual(len(results), 1)
            self.assertIsInstance(results[0], GeneratedArticle)
            self.assertEqual(results[0].title, "Título de prueba")
            self.assertEqual(
                results[0].introduction.questions[0].answer,
                "Respuesta simulada para prueba",
            )
            persisted = JsonGeneratedArticleRepository(temporary).load()
            self.assertEqual(persisted, results[0])

    def test_reports_safe_error_without_exposing_exception_details(self):
        secret = "clave-super-secreta"

        def failing_use_case_factory(provider_name, config, project_root):
            raise RuntimeError(secret)

        with tempfile.TemporaryDirectory() as temporary:
            worker = ArticleContentGeneratorWorker(
                self.plan,
                "fake",
                self.config,
                temporary,
                use_case_factory=failing_use_case_factory,
            )
            results = []
            errors = []
            worker.finished.connect(results.append)
            worker.failed.connect(errors.append)

            worker.run()

        self.assertEqual(results, [])
        self.assertEqual(errors, ["No se pudo generar el contenido del artículo."])
        self.assertNotIn(secret, errors[0])

    def test_translates_known_errors_to_safe_actionable_messages(self):
        secret = "clave-super-secreta"
        cases = [
            (
                SecretNotFoundError(secret),
                (
                    "Falta OPENAI_API_KEY. "
                    "Guárdala en Configuración."
                ),
            ),
            (
                AIProviderConfigurationError(secret),
                "Revisa la clave y la configuración de OpenAI.",
            ),
            (
                AIProviderTemporaryError(secret),
                (
                    "OpenAI no está disponible temporalmente. "
                    "Inténtalo de nuevo."
                ),
            ),
            (
                AIProviderResponseError(secret),
                (
                    "OpenAI devolvió una respuesta inválida. "
                    "Inténtalo de nuevo."
                ),
            ),
        ]

        for exception, expected_message in cases:
            with self.subTest(error_type=type(exception).__name__):
                def failing_use_case_factory(
                    provider_name,
                    config,
                    project_root,
                    *,
                    error=exception,
                ):
                    raise error

                with tempfile.TemporaryDirectory() as temporary:
                    worker = ArticleContentGeneratorWorker(
                        self.plan,
                        "openai",
                        self.config,
                        temporary,
                        use_case_factory=failing_use_case_factory,
                    )
                    results = []
                    errors = []
                    worker.finished.connect(results.append)
                    worker.failed.connect(errors.append)

                    worker.run()

                self.assertEqual(results, [])
                self.assertEqual(errors, [expected_message])
                self.assertNotIn(secret, errors[0])
                self.assertNotIn(str(exception), errors[0])

    def test_import_does_not_load_openai_sdk(self):
        script = (
            "import sys; "
            "import app.article_content_generator_worker; "
            "print('openai' in sys.modules)"
        )
        result = subprocess.run(
            [sys.executable, "-c", script],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.stdout.strip(), "False")

    def test_existing_master_worker_remains_available(self):
        from app.workers import MasterGeneratorWorker

        self.assertTrue(callable(MasterGeneratorWorker))


if __name__ == "__main__":
    unittest.main()
