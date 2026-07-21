from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from app.readers.bible_reader import read_bible_source


class BibleReaderTests(unittest.TestCase):
    def test_reads_utf8_text(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "citas.txt"
            path.write_text("Juan 3:16\nPorque Dios amó tanto al mundo.", encoding="utf-8")
            result = read_bible_source(path)
            self.assertEqual(result["format"], "txt")
            self.assertIn("Juan 3:16", result["text"])
            self.assertGreater(result["character_count"], 10)


if __name__ == "__main__":
    unittest.main()
