from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from app.project_service import create_project


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
            root = Path(project["root"])
            self.assertTrue((root / "proyecto.json").is_file())
            self.assertTrue((root / "fuente" / "articulo.pdf").is_file())
            self.assertTrue((root / "fuente" / "audio.mp3").is_file())
            self.assertTrue((root / "fuente" / "citas.txt").is_file())


if __name__ == "__main__":
    unittest.main()
