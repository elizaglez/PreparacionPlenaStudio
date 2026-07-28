import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from app.models import Project, ProjectSources
from app.source_processor import process_project_sources


class FakeArticle:
    title = "Artículo actualizado"
    sections = [{"number": 1}]
    detected_headings = ["Subtítulo"]
    unassigned_paragraphs = []
    parser_warnings = []

    def to_dict(self):
        return {
            "title": self.title,
            "introduction": "",
            "sections": self.sections,
            "boxes": [],
            "review_questions": [],
        }


class SourceProcessorTests(unittest.TestCase):
    def create_project(self, root: str) -> Project:
        return Project(
            name="Proyecto de prueba",
            root=root,
            sources=ProjectSources(
                pdf="fuente/articulo.pdf",
                audio="fuente/audio.mp3",
                bible="fuente/citas.txt",
            ),
            outputs={
                "generated_article": "trabajo/articulo_generado.json",
                "master": "trabajo/master.json",
                "master_validation": "trabajo/master_validacion.json",
                "pipeline_state": "trabajo/pipeline_estado.json",
                "generation_log": "trabajo/historial_generacion",
            },
        )

    def create_existing_outputs(self, root: Path) -> dict[str, Path]:
        work = root / "trabajo"
        output = root / "salidas"
        history = work / "historial_generacion"
        work.mkdir(exist_ok=True)
        output.mkdir(exist_ok=True)
        history.mkdir(exist_ok=True)

        paths = {
            "generated_article": work / "articulo_generado.json",
            "master": work / "master.json",
            "master_validation": work / "master_validacion.json",
            "pipeline_state": work / "pipeline_estado.json",
            "generated_word": output / "CONTENIDO_GENERADO.docx",
            "master_word": output / "MASTER.docx",
            "generation_log": history / "operacion.json",
        }
        paths["generated_article"].write_text(
            '{"title": "Artículo anterior"}',
            encoding="utf-8",
        )
        paths["master"].write_text(
            '{"title": "MASTER anterior"}',
            encoding="utf-8",
        )
        paths["master_validation"].write_text(
            '{"valid": true}',
            encoding="utf-8",
        )
        paths["pipeline_state"].write_text(
            '{"status": "complete"}',
            encoding="utf-8",
        )
        paths["generated_word"].write_bytes(b"contenido-exportado")
        paths["master_word"].write_bytes(b"master-exportado")
        paths["generation_log"].write_text(
            '{"operation": "generation"}',
            encoding="utf-8",
        )
        return paths

    def processing_patches(self, *, save_project=None):
        pdf_result = {
            "text": "Texto extraído",
            "pages": [],
            "page_count": 1,
            "character_count": 15,
            "questions": ["¿Pregunta?"],
            "scripture_references": [],
        }
        bible_result = {
            "text": "Texto bíblico",
            "character_count": 13,
        }
        audio_result = {
            "transcription_status": "disponible",
        }
        return (
            patch(
                "app.source_processor.read_pdf",
                return_value=pdf_result,
            ),
            patch(
                "app.source_processor.parse_article",
                return_value=FakeArticle(),
            ),
            patch(
                "app.source_processor.read_bible_source",
                return_value=bible_result,
            ),
            patch(
                "app.source_processor.inspect_audio",
                return_value=audio_result,
            ),
            patch(
                "app.source_processor.save_project",
                save_project or Mock(),
            ),
        )

    def test_invalidates_generated_article_after_successful_analysis(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = self.create_existing_outputs(root)
            work = root / "trabajo"
            project = self.create_project(temporary)
            patches = self.processing_patches()

            with (
                patches[0],
                patches[1],
                patches[2],
                patches[3],
                patches[4] as save_project,
            ):
                result = process_project_sources(project)

            self.assertFalse(paths["generated_article"].exists())
            self.assertNotIn("generated_article", project.outputs)

            archive_root = work / "archivados"
            archive_directories = list(archive_root.glob("master_*"))
            self.assertEqual(len(archive_directories), 1)
            archive = archive_directories[0]

            for key in (
                "master",
                "master_validation",
                "pipeline_state",
            ):
                with self.subTest(archived=key):
                    self.assertFalse(paths[key].exists())
                    archived_path = archive / paths[key].name
                    self.assertTrue(archived_path.is_file())
                    self.assertNotIn(key, project.outputs)

            for key in (
                "generated_word",
                "master_word",
                "generation_log",
            ):
                with self.subTest(preserved=key):
                    self.assertTrue(paths[key].is_file())

            self.assertEqual(
                project.outputs["generation_log"],
                "trabajo/historial_generacion",
            )
            self.assertTrue((work / "articulo.json").is_file())
            self.assertTrue((work / "fuentes_resumen.json").is_file())
            self.assertTrue((work / "pdf_extraido.txt").is_file())
            self.assertTrue((work / "citas_extraidas.txt").is_file())
            self.assertEqual(
                result["article"]["title"],
                "Artículo actualizado",
            )
            save_project.assert_called_once_with(project)

    def test_keeps_generated_article_when_analysis_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = self.create_existing_outputs(root)
            project = self.create_project(temporary)

            with (
                patch(
                    "app.source_processor.read_pdf",
                    return_value={"text": "Texto"},
                ),
                patch(
                    "app.source_processor.parse_article",
                    return_value=FakeArticle(),
                ),
                patch(
                    "app.source_processor.read_bible_source",
                    side_effect=RuntimeError("fallo de lectura"),
                ),
            ):
                with self.assertRaises(RuntimeError):
                    process_project_sources(project)

            for key in (
                "generated_article",
                "master",
                "master_validation",
                "pipeline_state",
            ):
                with self.subTest(preserved=key):
                    self.assertTrue(paths[key].is_file())
                    self.assertIn(key, project.outputs)

            self.assertFalse(
                (root / "trabajo" / "archivados").exists()
            )

    def test_keeps_generated_article_when_project_save_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = self.create_existing_outputs(root)
            project = self.create_project(temporary)
            previous_outputs = dict(project.outputs)
            save_error = RuntimeError("fallo al guardar proyecto")
            patches = self.processing_patches(
                save_project=Mock(side_effect=save_error),
            )

            with (
                patches[0],
                patches[1],
                patches[2],
                patches[3],
                patches[4],
            ):
                with self.assertRaises(RuntimeError):
                    process_project_sources(project)

            for key in (
                "generated_article",
                "master",
                "master_validation",
                "pipeline_state",
            ):
                with self.subTest(preserved=key):
                    self.assertTrue(paths[key].is_file())

            self.assertEqual(project.outputs, previous_outputs)
            self.assertFalse(
                (root / "trabajo" / "archivados").exists()
            )

    def test_uses_unique_archive_for_each_successful_analysis(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = self.create_project(temporary)
            first_paths = self.create_existing_outputs(root)
            first_patches = self.processing_patches()

            with (
                first_patches[0],
                first_patches[1],
                first_patches[2],
                first_patches[3],
                first_patches[4],
            ):
                process_project_sources(project)

            second_paths = self.create_existing_outputs(root)
            project.outputs.update(
                {
                    "master": "trabajo/master.json",
                    "master_validation": "trabajo/master_validacion.json",
                    "pipeline_state": "trabajo/pipeline_estado.json",
                }
            )
            second_patches = self.processing_patches()

            with (
                second_patches[0],
                second_patches[1],
                second_patches[2],
                second_patches[3],
                second_patches[4],
            ):
                process_project_sources(project)

            archive_directories = list(
                (root / "trabajo" / "archivados").glob("master_*")
            )
            self.assertEqual(len(archive_directories), 2)
            self.assertNotEqual(
                archive_directories[0].name,
                archive_directories[1].name,
            )
            self.assertFalse(first_paths["master"].exists())
            self.assertFalse(second_paths["master"].exists())


if __name__ == "__main__":
    unittest.main()
