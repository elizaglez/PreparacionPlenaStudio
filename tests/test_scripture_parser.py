import unittest

from app.parsers.scripture_parser import (
    extract_scripture_references,
    normalize_reference,
)


class ScriptureParserTests(unittest.TestCase):
    def test_normalizes_abbreviated_book(self):
        self.assertEqual(normalize_reference("Rom. 12:10"), "Romanos 12:10")

    def test_extracts_unique_references(self):
        text = "Lea Juan 3:16 y Rom. 12:10. Luego vuelva a Juan 3:16."
        refs = extract_scripture_references(text)
        self.assertEqual(refs, ["Juan 3:16", "Romanos 12:10"])


if __name__ == "__main__":
    unittest.main()
