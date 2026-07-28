import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QMessageBox

from app.generation.article_generation_plan import (
    ArticleGenerationPlanError,
)
from app.generation.generated_article import (
    GeneratedArticle,
    GeneratedBox,
    GeneratedIntroduction,
    GeneratedQuestion,
    GeneratedSection,
)
from app.models import Project
from app.pages.project_workspace import ProjectWorkspace
from app.persistence.generated_article_repository import (
    JsonGeneratedArticleRepository,
)


class ProjectWorkspaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def setUp(self):
        self.workspace = ProjectWorkspace()
        self.workspace.project = Project(
            name="Proyecto de prueba",
            root="C:/proyecto",
        )

    def tearDown(self):
        self.workspace.close()

    @staticmethod
    def generated_article():
        return GeneratedArticle(
            title="Artículo generado",
            introduction=GeneratedIntroduction(
                paragraphs=[
                    {
                        "number": 1,
                        "text": "Introducción fuente",
                    }
                ],
                questions=[
                    GeneratedQuestion(
                        number=1,
                        question="¿Pregunta inicial?",
                        answer="Respuesta inicial",
                        application="Aplicación inicial",
                    )
                ]
            ),
            sections=[
                GeneratedSection(
                    subtitle="Subtítulo",
                    heygen_transition="Transición de prueba",
                    questions=[
                        GeneratedQuestion(
                            number=2,
                            question="¿Pregunta de sección?",
                            answer="Respuesta de sección",
                            application="Aplicación de sección",
                        )
                    ],
                    section_summary="Resumen de la sección",
                    boxes=[
                        GeneratedBox(
                            title="Recuadro de prueba",
                            explanation="Explicación del recuadro",
                            linked_paragraph=2,
                        )
                    ],
                )
            ],
            review_questions=[
                "¿Qué aprendimos?",
            ],
        )

    def test_generate_button_identifies_content_generation(self):
        self.assertEqual(
            self.workspace.generate.text(),
            "2. GENERAR CONTENIDO",
        )

    def test_starts_composed_article_content_worker_after_confirmation(self):
        worker = Mock(name="article_content_worker")

        with (
            patch(
                "app.pages.project_workspace.QMessageBox.question",
                return_value=QMessageBox.StandardButton.Yes,
            ) as question,
            patch(
                "app.pages.project_workspace.create_article_content_worker",
                return_value=worker,
            ) as worker_factory,
            patch.object(self.workspace, "_start_worker") as start_worker,
        ):
            self.workspace.generate_article_content()

        question.assert_called_once_with(
            self.workspace,
            "Generar contenido",
            "Se enviará una solicitud a OpenAI por cada pregunta detectada. "
            "Esto puede generar costos de API. ¿Continuar?",
        )
        worker_factory.assert_called_once_with(self.workspace.project)
        start_worker.assert_called_once_with(worker, "article_content")

    def test_does_not_create_worker_when_generation_is_cancelled(self):
        with (
            patch(
                "app.pages.project_workspace.QMessageBox.question",
                return_value=QMessageBox.StandardButton.No,
            ),
            patch(
                "app.pages.project_workspace.create_article_content_worker",
            ) as worker_factory,
            patch.object(self.workspace, "_start_worker") as start_worker,
        ):
            self.workspace.generate_article_content()

        worker_factory.assert_not_called()
        start_worker.assert_not_called()

    def test_confirmed_regeneration_starts_article_content_worker(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = Project(
                name="Proyecto con contenido",
                root=temporary,
            )
            JsonGeneratedArticleRepository(temporary).save(
                self.generated_article()
            )
            self.workspace.project = project
            worker = Mock(name="article_content_worker")

            with (
                patch(
                    "app.pages.project_workspace.QMessageBox.question",
                    return_value=QMessageBox.StandardButton.Yes,
                ) as question,
                patch(
                    "app.pages.project_workspace."
                    "create_article_content_worker",
                    return_value=worker,
                ) as worker_factory,
                patch.object(
                    self.workspace,
                    "_start_worker",
                ) as start_worker,
            ):
                self.workspace.generate_article_content()

            question.assert_called_once_with(
                self.workspace,
                "Regenerar contenido",
                "Ya existe contenido generado. Si continúas, se reemplazará "
                "el contenido anterior. Se enviará una solicitud a OpenAI "
                "por cada pregunta detectada y esto puede generar costos "
                "de API. ¿Continuar?",
            )
            worker_factory.assert_called_once_with(project)
            start_worker.assert_called_once_with(
                worker,
                "article_content",
            )

    def test_cancelled_regeneration_preserves_generated_article(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = Project(
                name="Proyecto con contenido",
                root=temporary,
            )
            repository = JsonGeneratedArticleRepository(temporary)
            repository.save(self.generated_article())
            previous_content = repository.path.read_bytes()
            self.workspace.project = project

            with (
                patch(
                    "app.pages.project_workspace.QMessageBox.question",
                    return_value=QMessageBox.StandardButton.No,
                ) as question,
                patch(
                    "app.pages.project_workspace."
                    "create_article_content_worker",
                ) as worker_factory,
                patch.object(
                    self.workspace,
                    "_start_worker",
                ) as start_worker,
            ):
                self.workspace.generate_article_content()

            question.assert_called_once_with(
                self.workspace,
                "Regenerar contenido",
                "Ya existe contenido generado. Si continúas, se reemplazará "
                "el contenido anterior. Se enviará una solicitud a OpenAI "
                "por cada pregunta detectada y esto puede generar costos "
                "de API. ¿Continuar?",
            )
            worker_factory.assert_not_called()
            start_worker.assert_not_called()
            self.assertEqual(
                repository.path.read_bytes(),
                previous_content,
            )

    def test_valid_master_does_not_activate_regeneration_warning(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary) / "trabajo"
            work.mkdir()
            (work / "master.json").write_text(
                json.dumps(
                    {
                        "title": "MASTER legacy",
                        "answers": [],
                    }
                ),
                encoding="utf-8",
            )
            project = Project(
                name="Proyecto con MASTER",
                root=temporary,
            )
            self.workspace.project = project

            with (
                patch(
                    "app.pages.project_workspace.QMessageBox.question",
                    return_value=QMessageBox.StandardButton.No,
                ) as question,
                patch(
                    "app.pages.project_workspace."
                    "create_article_content_worker",
                ) as worker_factory,
                patch.object(
                    self.workspace,
                    "_start_worker",
                ) as start_worker,
            ):
                self.workspace.generate_article_content()

            question.assert_called_once_with(
                self.workspace,
                "Generar contenido",
                "Se enviará una solicitud a OpenAI por cada pregunta detectada. "
                "Esto puede generar costos de API. ¿Continuar?",
            )
            worker_factory.assert_not_called()
            start_worker.assert_not_called()

    def test_reports_actionable_error_for_empty_generation_plan(self):
        internal_detail = "detalle interno que no debe mostrarse"

        with (
            patch(
                "app.pages.project_workspace.QMessageBox.question",
                return_value=QMessageBox.StandardButton.Yes,
            ),
            patch(
                "app.pages.project_workspace."
                "create_article_content_worker",
                side_effect=ArticleGenerationPlanError(
                    internal_detail
                ),
            ) as worker_factory,
            patch(
                "app.pages.project_workspace.QMessageBox.critical",
            ) as critical,
            patch.object(
                self.workspace,
                "_start_worker",
            ) as start_worker,
        ):
            self.workspace.generate_article_content()

        worker_factory.assert_called_once_with(self.workspace.project)
        start_worker.assert_not_called()
        critical.assert_called_once_with(
            self.workspace,
            "Error",
            "No se detectaron preguntas utilizables. "
            "Revisa las fuentes y vuelve a analizar el artículo "
            "antes de generar contenido.",
        )
        self.assertNotIn(
            internal_detail,
            critical.call_args.args[2],
        )

    def test_reports_worker_composition_failure_without_starting_thread(self):
        with (
            patch(
                "app.pages.project_workspace.QMessageBox.question",
                return_value=QMessageBox.StandardButton.Yes,
            ),
            patch(
                "app.pages.project_workspace.create_article_content_worker",
                side_effect=ValueError("detalle interno"),
            ),
            patch(
                "app.pages.project_workspace.QMessageBox.critical",
            ) as critical,
            patch.object(self.workspace, "_start_worker") as start_worker,
        ):
            self.workspace.generate_article_content()

        start_worker.assert_not_called()
        critical.assert_called_once_with(
            self.workspace,
            "Error",
            "No se pudo preparar la generación del artículo.",
        )

    def test_handles_generated_article_completion(self):
        dialog = Mock()
        self.workspace.processing_dialog = dialog
        self.workspace.current_operation = "article_content"

        self.workspace._operation_finished(self.generated_article())

        self.assertEqual(
            self.workspace.status.text(),
            "Contenido del artículo generado.",
        )
        diagnostics = self.workspace.diagnostics.toPlainText()
        self.assertIn("Artículo generado", diagnostics)
        self.assertIn("Preguntas: 2", diagnostics)
        self.assertIn("Respuestas generadas: 2", diagnostics)
        self.assertIn("trabajo/articulo_generado.json", diagnostics)
        self.assertIn("Introducción fuente", diagnostics)
        self.assertIn("¿Pregunta inicial?", diagnostics)
        self.assertIn("Respuesta: Respuesta inicial", diagnostics)
        self.assertIn("Aplicación: Aplicación inicial", diagnostics)
        self.assertIn("Subtítulo", diagnostics)
        self.assertIn("Transición: Transición de prueba", diagnostics)
        self.assertIn("¿Pregunta de sección?", diagnostics)
        self.assertIn("Respuesta: Respuesta de sección", diagnostics)
        self.assertIn("Aplicación: Aplicación de sección", diagnostics)
        self.assertIn("Resumen: Resumen de la sección", diagnostics)
        self.assertIn("RECUADRO: Recuadro de prueba", diagnostics)
        self.assertIn("Explicación del recuadro", diagnostics)
        self.assertIn("PREGUNTAS DE REPASO", diagnostics)
        self.assertIn("• ¿Qué aprendimos?", diagnostics)
        dialog.mark_finished.assert_called_once_with(
            "Listo. Se creó trabajo/articulo_generado.json."
        )

    def test_generated_article_view_omits_empty_optional_fields(self):
        article = GeneratedArticle(
            title="Artículo mínimo",
            introduction=GeneratedIntroduction(
                questions=[
                    GeneratedQuestion(
                        number=1,
                        question="¿Pregunta sin respuesta?",
                    )
                ]
            ),
            sections=[
                GeneratedSection(
                    subtitle="Sección mínima",
                    heygen_transition="",
                    questions=[],
                    section_summary="",
                    boxes=[
                        GeneratedBox(
                            title="",
                            explanation="",
                            linked_paragraph=1,
                        )
                    ],
                )
            ],
            review_questions=["", "   "],
        )

        self.workspace._show_generated_article(article)

        diagnostics = self.workspace.diagnostics.toPlainText()
        self.assertIn("¿Pregunta sin respuesta?", diagnostics)
        self.assertIn("Sección mínima", diagnostics)
        self.assertNotIn("Respuesta:", diagnostics)
        self.assertNotIn("Aplicación:", diagnostics)
        self.assertNotIn("Transición:", diagnostics)
        self.assertNotIn("Resumen:", diagnostics)
        self.assertNotIn("RECUADRO", diagnostics)
        self.assertNotIn("PREGUNTAS DE REPASO", diagnostics)

    def test_refreshes_persisted_generated_article(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = Project(
                name="Proyecto persistido",
                root=temporary,
            )
            work = Path(temporary) / "trabajo"
            work.mkdir()
            (work / "articulo.json").write_text(
                '{"title": "Fuente", "sections": []}',
                encoding="utf-8",
            )
            JsonGeneratedArticleRepository(temporary).save(
                self.generated_article()
            )
            self.workspace.project = project

            self.workspace._refresh_outputs()

        self.assertTrue(self.workspace.generate.isEnabled())
        self.assertTrue(self.workspace.export.isEnabled())
        self.assertEqual(
            self.workspace.status.text(),
            "Contenido del artículo generado.",
        )
        self.assertIn(
            "Artículo generado",
            self.workspace.diagnostics.toPlainText(),
        )

    def test_generated_article_has_display_priority_over_legacy_master(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = Project(
                name="Proyecto con ambas salidas",
                root=temporary,
            )
            work = Path(temporary) / "trabajo"
            work.mkdir()
            (work / "articulo.json").write_text(
                '{"title": "Fuente", "sections": []}',
                encoding="utf-8",
            )
            (work / "master.json").write_text(
                json.dumps(
                    {
                        "title": "MASTER anterior",
                        "model": "modelo-legacy",
                        "answers": [],
                    }
                ),
                encoding="utf-8",
            )
            JsonGeneratedArticleRepository(temporary).save(
                self.generated_article()
            )
            self.workspace.project = project

            self.workspace._refresh_outputs()

        self.assertTrue(self.workspace.export.isEnabled())
        self.assertEqual(
            self.workspace.status.text(),
            "Contenido del artículo generado.",
        )
        diagnostics = self.workspace.diagnostics.toPlainText()
        self.assertIn("Artículo generado", diagnostics)
        self.assertNotIn("MASTER anterior", diagnostics)

    def test_exports_generated_article_with_priority_over_legacy_master(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary) / "trabajo"
            work.mkdir()
            JsonGeneratedArticleRepository(temporary).save(
                self.generated_article()
            )
            (work / "master.json").write_text("{}", encoding="utf-8")
            self.workspace.project = Project(
                name="Proyecto con ambas salidas",
                root=temporary,
            )
            generated_output = (
                Path(temporary) / "salidas" / "CONTENIDO_GENERADO.docx"
            )

            with (
                patch(
                    "app.pages.project_workspace."
                    "export_generated_article_to_docx",
                    return_value=generated_output,
                ) as generated_exporter,
                patch(
                    "app.pages.project_workspace.export_master_to_docx",
                ) as legacy_exporter,
                patch.object(self.workspace, "_refresh_outputs"),
                patch(
                    "app.pages.project_workspace.QMessageBox.information",
                ),
            ):
                self.workspace.export_word()

        generated_exporter.assert_called_once_with(self.workspace.project)
        legacy_exporter.assert_not_called()

    def test_exports_legacy_master_when_generated_article_is_absent(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary) / "trabajo"
            work.mkdir()
            (work / "master.json").write_text("{}", encoding="utf-8")
            self.workspace.project = Project(
                name="Proyecto legacy",
                root=temporary,
            )
            legacy_output = Path(temporary) / "salidas" / "MASTER.docx"

            with (
                patch(
                    "app.pages.project_workspace."
                    "export_generated_article_to_docx",
                ) as generated_exporter,
                patch(
                    "app.pages.project_workspace.export_master_to_docx",
                    return_value=legacy_output,
                ) as legacy_exporter,
                patch.object(self.workspace, "_refresh_outputs"),
                patch(
                    "app.pages.project_workspace.QMessageBox.information",
                ),
            ):
                self.workspace.export_word()

        generated_exporter.assert_not_called()
        legacy_exporter.assert_called_once_with(self.workspace.project)

    def test_invalid_generated_article_falls_back_to_valid_master(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary) / "trabajo"
            work.mkdir()
            generated_path = work / "articulo_generado.json"
            generated_path.write_text(
                "{json inválido",
                encoding="utf-8",
            )
            master_path = work / "master.json"
            master_path.write_text(
                json.dumps(
                    {
                        "title": "MASTER recuperable",
                        "model": "modelo-legacy",
                        "answers": [],
                    }
                ),
                encoding="utf-8",
            )
            self.workspace.project = Project(
                name="Proyecto con fallback",
                root=temporary,
            )

            self.workspace._refresh_outputs()

            self.assertTrue(self.workspace.export.isEnabled())
            self.assertEqual(
                self.workspace.status.text(),
                "MASTER generado, validado y listo para revisar.",
            )
            diagnostics = self.workspace.diagnostics.toPlainText()
            self.assertIn("MASTER recuperable", diagnostics)
            self.assertTrue(generated_path.is_file())
            self.assertTrue(master_path.is_file())

    def test_exports_valid_master_when_generated_article_is_invalid(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary) / "trabajo"
            work.mkdir()
            generated_path = work / "articulo_generado.json"
            generated_path.write_text(
                "{json inválido",
                encoding="utf-8",
            )
            master_path = work / "master.json"
            master_path.write_text(
                json.dumps(
                    {
                        "title": "MASTER válido",
                        "answers": [],
                    }
                ),
                encoding="utf-8",
            )
            self.workspace.project = Project(
                name="Proyecto con fallback",
                root=temporary,
            )
            legacy_output = Path(temporary) / "salidas" / "MASTER.docx"

            with (
                patch(
                    "app.pages.project_workspace."
                    "export_generated_article_to_docx",
                ) as generated_exporter,
                patch(
                    "app.pages.project_workspace.export_master_to_docx",
                    return_value=legacy_output,
                ) as legacy_exporter,
                patch.object(self.workspace, "_refresh_outputs"),
                patch(
                    "app.pages.project_workspace.QMessageBox.information",
                ),
            ):
                self.workspace.export_word()

            generated_exporter.assert_not_called()
            legacy_exporter.assert_called_once_with(self.workspace.project)
            self.assertTrue(generated_path.is_file())
            self.assertTrue(master_path.is_file())

    def test_disables_export_when_no_generated_output_is_valid(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary) / "trabajo"
            work.mkdir()
            generated_path = work / "articulo_generado.json"
            generated_path.write_text(
                "{json inválido",
                encoding="utf-8",
            )
            master_path = work / "master.json"
            master_path.write_text(
                "[\"MASTER inválido\"]",
                encoding="utf-8",
            )
            self.workspace.project = Project(
                name="Proyecto sin salida válida",
                root=temporary,
            )

            self.workspace._refresh_outputs()

            self.assertFalse(self.workspace.export.isEnabled())
            self.assertEqual(
                self.workspace.status.text(),
                "No hay una salida válida para exportar.",
            )
            self.assertIn(
                "No se pudieron leer los archivos generados.",
                self.workspace.diagnostics.toPlainText(),
            )
            self.assertTrue(generated_path.is_file())
            self.assertTrue(master_path.is_file())

    def test_reports_safe_error_when_export_has_no_valid_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary) / "trabajo"
            work.mkdir()
            generated_path = work / "articulo_generado.json"
            generated_path.write_text(
                "{detalle interno inválido",
                encoding="utf-8",
            )
            self.workspace.project = Project(
                name="Proyecto sin salida válida",
                root=temporary,
            )

            with (
                patch(
                    "app.pages.project_workspace."
                    "export_generated_article_to_docx",
                ) as generated_exporter,
                patch(
                    "app.pages.project_workspace.export_master_to_docx",
                ) as legacy_exporter,
                patch(
                    "app.pages.project_workspace.QMessageBox.critical",
                ) as critical,
            ):
                self.workspace.export_word()

            generated_exporter.assert_not_called()
            legacy_exporter.assert_not_called()
            critical.assert_called_once_with(
                self.workspace,
                "Error al exportar",
                "No hay una salida válida para exportar.",
            )
            self.assertTrue(generated_path.is_file())

    def test_legacy_generate_master_route_remains_unchanged(self):
        worker = Mock(name="master_worker")

        with (
            patch(
                "app.pages.project_workspace.QMessageBox.question",
                return_value=QMessageBox.StandardButton.Yes,
            ) as question,
            patch(
                "app.pages.project_workspace.MasterGeneratorWorker",
                return_value=worker,
            ) as worker_type,
            patch.object(self.workspace, "_start_worker") as start_worker,
        ):
            self.workspace.generate_master()

        question.assert_called_once_with(
            self.workspace,
            "Generar MASTER",
            "Se enviará una solicitud a OpenAI por cada pregunta detectada. "
            "Esto puede generar costos de API. ¿Continuar?",
        )
        worker_type.assert_called_once_with(self.workspace.project)
        start_worker.assert_called_once_with(worker, "master")


if __name__ == "__main__":
    unittest.main()
