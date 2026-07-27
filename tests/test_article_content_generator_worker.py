import subprocess
import sys
import unittest

from app.ai.config import AIProviderConfig
from app.article_content_generator_worker import ArticleContentGeneratorWorker
from app.generation.article_generation_plan import (
    ArticleGenerationPlan,
    GenerationSection,
    QuestionSource,
)
from app.generation.generated_article import GeneratedArticle


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

    def test_generates_with_fake_provider_and_reports_progress(self):
        worker = ArticleContentGeneratorWorker(
            self.plan,
            "fake",
            self.config,
        )
        progress = []
        results = []
        errors = []
        worker.progress.connect(lambda value, message: progress.append((value, message)))
        worker.finished.connect(results.append)
        worker.failed.connect(errors.append)

        worker.run()

        self.assertEqual(errors, [])
        self.assertEqual([value for value, _ in progress], [0, 10, 100])
        self.assertEqual(len(results), 1)
        self.assertIsInstance(results[0], GeneratedArticle)
        self.assertEqual(results[0].title, "Título de prueba")
        self.assertEqual(len(results[0].introduction.questions), 1)
        self.assertEqual(
            results[0].introduction.questions[0].answer,
            "Respuesta simulada para prueba",
        )

    def test_reports_safe_error_without_exposing_exception_details(self):
        secret = "clave-super-secreta"

        def failing_service_factory(provider_name, config):
            raise RuntimeError(secret)

        worker = ArticleContentGeneratorWorker(
            self.plan,
            "fake",
            self.config,
            service_factory=failing_service_factory,
        )
        results = []
        errors = []
        worker.finished.connect(results.append)
        worker.failed.connect(errors.append)

        worker.run()

        self.assertEqual(results, [])
        self.assertEqual(errors, ["No se pudo generar el contenido del artículo."])
        self.assertNotIn(secret, errors[0])

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
