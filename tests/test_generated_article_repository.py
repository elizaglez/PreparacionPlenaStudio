import inspect
import json
import tempfile
import unittest
from pathlib import Path

from app.generation.generated_article import (
    GeneratedArticle,
    GeneratedBox,
    GeneratedIntroduction,
    GeneratedQuestion,
    GeneratedSection,
)
from app.persistence.generated_article_repository import (
    GENERATED_ARTICLE_SCHEMA_VERSION,
    GeneratedArticleRepository,
    GeneratedArticleRepositoryError,
    JsonGeneratedArticleRepository,
)


class GeneratedArticleRepositoryTests(unittest.TestCase):
    def test_saves_and_loads_complete_generated_article(self):
        article = GeneratedArticle(
            title="Título",
            introduction=GeneratedIntroduction(
                paragraphs=[{"number": 1, "text": "Introducción"}],
                questions=[
                    GeneratedQuestion(
                        number=1,
                        question="¿Pregunta inicial?",
                        answer="Respuesta inicial",
                        application="Aplicación inicial",
                    )
                ],
            ),
            sections=[
                GeneratedSection(
                    subtitle="SUBTÍTULO",
                    heygen_transition="Transición",
                    questions=[
                        GeneratedQuestion(
                            number=2,
                            question="¿Pregunta?",
                            answer="Respuesta",
                            application="Aplicación",
                        )
                    ],
                    section_summary="Resumen",
                    boxes=[
                        GeneratedBox(
                            title="Recuadro",
                            explanation="Explicación",
                            linked_paragraph=2,
                        )
                    ],
                )
            ],
            review_questions=["¿Repaso?"],
        )

        with tempfile.TemporaryDirectory() as temporary:
            repository = JsonGeneratedArticleRepository(temporary)

            repository.save(article)
            restored = repository.load()

            self.assertEqual(restored, article)
            self.assertEqual(
                repository.path,
                Path(temporary) / "trabajo" / "articulo_generado.json",
            )
            self.assertFalse(repository.path.with_suffix(".json.tmp").exists())
            data = json.loads(repository.path.read_text(encoding="utf-8"))
            self.assertEqual(
                data["schema_version"], GENERATED_ARTICLE_SCHEMA_VERSION
            )

    def test_loads_legacy_file_without_schema_version(self):
        article = GeneratedArticle(title="Artículo antiguo")
        with tempfile.TemporaryDirectory() as temporary:
            repository = JsonGeneratedArticleRepository(temporary)
            repository.path.parent.mkdir(parents=True, exist_ok=True)
            repository.path.write_text(
                json.dumps(article.to_dict(), ensure_ascii=False),
                encoding="utf-8",
            )

            self.assertEqual(repository.load(), article)

    def test_registers_output_in_existing_project(self):
        article = GeneratedArticle(title="Artículo de proyecto")
        with tempfile.TemporaryDirectory() as temporary:
            project_path = Path(temporary) / "proyecto.json"
            project_path.write_text(
                json.dumps(
                    {
                        "name": "Proyecto",
                        "root": temporary,
                        "outputs": {},
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            repository = JsonGeneratedArticleRepository(temporary)

            repository.save(article)

            project_data = json.loads(project_path.read_text(encoding="utf-8"))
            self.assertEqual(
                project_data["outputs"]["generated_article"],
                "trabajo/articulo_generado.json",
            )

    def test_missing_article_raises_repository_error(self):
        with tempfile.TemporaryDirectory() as temporary:
            repository = JsonGeneratedArticleRepository(temporary)

            with self.assertRaises(GeneratedArticleRepositoryError):
                repository.load()

    def test_contract_and_implementation_have_no_ai_or_ui_dependencies(self):
        self.assertTrue(
            issubclass(JsonGeneratedArticleRepository, GeneratedArticleRepository)
        )
        module = inspect.getmodule(JsonGeneratedArticleRepository)
        self.assertIsNotNone(module)
        source = inspect.getsource(module)
        self.assertNotIn("openai", source.casefold())
        self.assertNotIn("pyside", source.casefold())
        self.assertNotIn("AIProvider", source)


if __name__ == "__main__":
    unittest.main()
