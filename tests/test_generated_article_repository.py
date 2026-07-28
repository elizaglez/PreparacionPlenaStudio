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
            project_path = Path(temporary) / "proyecto.json"

            def fail_after_partial_project_save(_project):
                project_path.write_bytes(b'{"status": "contenido_')
                raise RuntimeError("fallo al guardar")

            with (
                patch(
                    "app.persistence.generated_article_repository.save_project",
                    side_effect=fail_after_partial_project_save,
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
            self.assertFalse(repository.path.exists())
            self.assertFalse(project_path.exists())

    def test_restores_previous_article_and_project_when_save_fails(self):
        previous_content = (
            b'{\n'
            b'  "schema_version": 1,\n'
            b'  "title": "Articulo anterior",\n'
            b'  "introduction": {"paragraphs": [], "questions": []},\n'
            b'  "sections": [],\n'
            b'  "review_questions": []\n'
            b'}'
        )
        previous_project_content = (
            b'{\n'
            b'  "name": "Proyecto con articulo anterior",\n'
            b'  "status": "contenido_generado",\n'
            b'  "updated_at": "2026-01-01T10:00:00-06:00",\n'
            b'  "outputs": {\n'
            b'    "article": "trabajo/articulo.json",\n'
            b'    "generated_article": '
            b'"trabajo/articulo_generado.json"\n'
            b'  }\n'
            b'}'
        )
        replacement = GeneratedArticle(title="Artículo nuevo")

        with tempfile.TemporaryDirectory() as temporary:
            project = Project(
                name="Proyecto con artículo anterior",
                root=temporary,
                status="contenido_generado",
                updated_at="2026-01-01T10:00:00-06:00",
                outputs={
                    "article": "trabajo/articulo.json",
                    "generated_article": (
                        "trabajo/articulo_generado.json"
                    ),
                },
            )
            previous_outputs = dict(project.outputs)
            repository = JsonGeneratedArticleRepository(
                temporary,
                project=project,
            )
            repository.path.parent.mkdir(parents=True)
            repository.path.write_bytes(previous_content)
            project_path = Path(temporary) / "proyecto.json"
            project_path.write_bytes(previous_project_content)

            def fail_after_partial_project_save(_project):
                project_path.write_bytes(b'{"status": "contenido_')
                raise RuntimeError("fallo al guardar")

            with (
                patch(
                    "app.persistence.generated_article_repository.save_project",
                    side_effect=fail_after_partial_project_save,
                ),
                self.assertRaises(RuntimeError),
            ):
                repository.save(replacement)

            self.assertEqual(
                repository.path.read_bytes(),
                previous_content,
            )
            self.assertEqual(
                project_path.read_bytes(),
                previous_project_content,
            )
            self.assertEqual(project.status, "contenido_generado")
            self.assertEqual(
                project.updated_at,
                "2026-01-01T10:00:00-06:00",
            )
            self.assertEqual(project.outputs, previous_outputs)

    def test_successful_save_replaces_previous_article(self):
        replacement = GeneratedArticle(title="Artículo nuevo")
        with tempfile.TemporaryDirectory() as temporary:
            repository = JsonGeneratedArticleRepository(temporary)
            repository.path.parent.mkdir(parents=True)
            repository.path.write_text(
                '{"title": "Artículo anterior"}',
                encoding="utf-8",
            )

            repository.save(replacement)

            self.assertEqual(repository.load(), replacement)

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
