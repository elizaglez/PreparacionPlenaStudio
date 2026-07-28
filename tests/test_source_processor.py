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
            },
        )

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
            work = root / "trabajo"
            output = root / "salidas"
            work.mkdir()
            output.mkdir()
            generated_path = work / "articulo_generado.json"
            generated_path.write_text(
                '{"title": "Artículo anterior"}',
                encoding="utf-8",
            )
            word_path = output / "CONTENIDO_GENERADO.docx"
            word_path.write_bytes(b"documento-exportado")
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

            self.assertFalse(generated_path.exists())
            self.assertTrue(word_path.is_file())
            self.assertNotIn("generated_article", project.outputs)
            self.assertTrue((work / "articulo.json").is_file())
            self.assertTrue((work / "fuentes_resumen.json").is_file())
            self.assertEqual(
                result["article"]["title"],
                "Artículo actualizado",
            )
            save_project.assert_called_once_with(project)

    def test_keeps_generated_article_when_analysis_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            work = root / "trabajo"
            work.mkdir()
            generated_path = work / "articulo_generado.json"
            generated_path.write_text(
                '{"title": "Artículo anterior"}',
                encoding="utf-8",
            )
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

            self.assertTrue(generated_path.is_file())
            self.assertEqual(
                project.outputs["generated_article"],
                "trabajo/articulo_generado.json",
            )

    def test_keeps_generated_article_when_project_save_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            work = root / "trabajo"
            work.mkdir()
            generated_path = work / "articulo_generado.json"
            generated_path.write_text(
                '{"title": "Artículo anterior"}',
                encoding="utf-8",
            )
            project = self.create_project(temporary)
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

            self.assertTrue(generated_path.is_file())
            self.assertEqual(
                project.outputs["generated_article"],
                "trabajo/articulo_generado.json",
            )


if __name__ == "__main__":
    unittest.main()
