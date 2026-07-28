import inspect
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.generation.generated_article import (
    GeneratedArticle,
    GeneratedBox,
    GeneratedIntroduction,
    GeneratedQuestion,
    GeneratedSection,
)
from app.models import Project
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

    def test_updates_current_project_and_persists_generation_metadata(self):
        article = GeneratedArticle(title="Artículo actualizado")
        with tempfile.TemporaryDirectory() as temporary:
            project = Project(
                name="Proyecto actual",
                root=temporary,
                status="articulo_estructurado",
                updated_at="2026-01-01T10:00:00-06:00",
                outputs={"article": "trabajo/articulo.json"},
            )
            repository = JsonGeneratedArticleRepository(
                temporary,
                project=project,
            )

            repository.save(article)

            self.assertEqual(project.status, "contenido_generado")
            self.assertNotEqual(
                project.updated_at,
                "2026-01-01T10:00:00-06:00",
            )
            self.assertEqual(
                project.outputs["generated_article"],
                "trabajo/articulo_generado.json",
            )

            project_data = json.loads(
                (Path(temporary) / "proyecto.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(
                project_data["status"],
                "contenido_generado",
            )
            self.assertEqual(
                project_data["updated_at"],
                project.updated_at,
            )
            self.assertEqual(
                project_data["outputs"]["generated_article"],
                "trabajo/articulo_generado.json",
            )

    def test_restores_current_project_when_project_save_fails(self):
        article = GeneratedArticle(title="Artículo no confirmado")
        with tempfile.TemporaryDirectory() as temporary:
            previous_outputs = {
                "article": "trabajo/articulo.json",
            }
            project = Project(
                name="Proyecto con fallo",
                root=temporary,
                status="articulo_estructurado",
                updated_at="2026-01-01T10:00:00-06:00",
                outputs=dict(previous_outputs),
            )
            repository = JsonGeneratedArticleRepository(
                temporary,
                project=project,
            )

            with (
                patch(
                    "app.persistence.generated_article_repository.save_project",
                    side_effect=RuntimeError("fallo al guardar"),
                ),
                self.assertRaises(RuntimeError),
            ):
                repository.save(article)

            self.assertEqual(project.status, "articulo_estructurado")
            self.assertEqual(
                project.updated_at,
                "2026-01-01T10:00:00-06:00",
            )
            self.assertEqual(project.outputs, previous_outputs)

    def test_path_only_repository_updates_existing_project_metadata(self):
        article = GeneratedArticle(title="Artículo por ruta")
        with tempfile.TemporaryDirectory() as temporary:
            project_path = Path(temporary) / "proyecto.json"
            project_path.write_text(
                json.dumps(
                    {
                        "name": "Proyecto por ruta",
                        "root": temporary,
                        "status": "articulo_estructurado",
                        "updated_at": "fecha-anterior",
                        "outputs": {},
                    }
                ),
                encoding="utf-8",
            )
            repository = JsonGeneratedArticleRepository(temporary)

            repository.save(article)

            project_data = json.loads(
                project_path.read_text(encoding="utf-8")
            )
            self.assertEqual(
                project_data["status"],
                "contenido_generado",
            )
            self.assertNotEqual(
                project_data["updated_at"],
                "fecha-anterior",
            )
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
