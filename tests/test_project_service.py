from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from app.project_service import ProjectError, create_project


class ProjectServiceTests(unittest.TestCase):
    def test_creates_project_structure(self):
        with TemporaryDirectory() as folder:
            base = Path(folder)
            pdf = base / "a.pdf"
            audio = base / "a.mp3"
            bible = base / "citas.txt"
            pdf.write_bytes(b"%PDF-1.4\n")
            audio.write_bytes(b"ID3")
            bible.write_text("Juan 3:16", encoding="utf-8")

            project = create_project(
                "Proyecto prueba", str(base / "projects"),
                str(pdf), str(audio), str(bible)
            )
            root = Path(project.root)
            self.assertTrue((root / "proyecto.json").is_file())
            self.assertTrue((root / "fuente" / "articulo.pdf").is_file())
            self.assertTrue((root / "fuente" / "audio.mp3").is_file())
            self.assertTrue((root / "fuente" / "citas.txt").is_file())

    def test_rejects_invalid_audio_extension_without_creating_project(self):
        with TemporaryDirectory() as folder:
            base = Path(folder)
            pdf = base / "a.pdf"
            audio = base / "a.ogg"
            bible = base / "citas.txt"
            pdf.write_bytes(b"%PDF-1.4\n")
            audio.write_bytes(b"audio")
            bible.write_text("Juan 3:16", encoding="utf-8")
            projects = base / "projects"

            with self.assertRaisesRegex(
                ProjectError,
                "El audio debe ser MP3, WAV o M4A",
            ):
                create_project(
                    "Proyecto inválido",
                    str(projects),
                    str(pdf),
                    str(audio),
                    str(bible),
                )

            self.assertFalse(projects.exists())

    def test_rejects_invalid_bible_extension_without_creating_project(self):
        with TemporaryDirectory() as folder:
            base = Path(folder)
            pdf = base / "a.pdf"
            audio = base / "a.mp3"
            bible = base / "citas.rtf"
            pdf.write_bytes(b"%PDF-1.4\n")
            audio.write_bytes(b"ID3")
            bible.write_text("Juan 3:16", encoding="utf-8")
            projects = base / "projects"

            with self.assertRaisesRegex(
                ProjectError,
                "El archivo de citas debe ser TXT, DOCX o PDF",
            ):
                create_project(
                    "Proyecto inválido",
                    str(projects),
                    str(pdf),
                    str(audio),
                    str(bible),
                )

            self.assertFalse(projects.exists())


if __name__ == "__main__":
    unittest.main()
