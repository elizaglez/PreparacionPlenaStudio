import unittest
from unittest.mock import patch

from app.readers.ocr_reader import OcrUnavailableError, read_page_with_ocr


class FakePage:
    def __init__(self, words=None):
        self.ocr_calls = []
        self.words = words or []

    def get_textpage_ocr(self, **kwargs):
        self.ocr_calls.append(kwargs)
        return "ocr-text-page"

    def get_text(self, kind, *, textpage, sort=False):
        self.assert_text_page(textpage)
        if kind == "words":
            return self.words
        if kind == "text":
            return "Texto reconocido\n"
        return [
            (10, 20, 110, 60, "Bloque reconocido", 2, 0),
        ]

    @staticmethod
    def assert_text_page(value):
        if value != "ocr-text-page":
            raise AssertionError("Página de texto OCR incorrecta")


class OcrReaderTests(unittest.TestCase):
    @patch("app.readers.ocr_reader.fitz.get_tessdata", return_value="tessdata")
    def test_extracts_text_and_blocks(self, get_tessdata):
        page = FakePage()

        result = read_page_with_ocr(page)

        get_tessdata.assert_called_once_with()
        self.assertEqual(result["text"], "Texto reconocido")
        self.assertEqual(result["blocks"][0]["block_no"], 2)
        self.assertEqual(result["blocks"][0]["bbox"], [10, 20, 110, 60])
        self.assertEqual(
            page.ocr_calls,
            [
                {
                    "language": "spa",
                    "dpi": 300,
                    "full": True,
                    "tessdata": "tessdata",
                }
            ],
        )

    @patch("app.readers.ocr_reader.fitz.get_tessdata", return_value="tessdata")
    def test_orders_columns_and_preserves_numbered_structure(self, get_tessdata):
        words = [
            (20, 10, 70, 20, "TÍTULO", 0, 0, 0),
            (20, 40, 25, 50, "1", 1, 0, 0),
            (29, 40, 70, 50, "Primer", 1, 0, 1),
            (74, 40, 115, 50, "párrafo", 1, 0, 2),
            (20, 60, 25, 70, "1", 2, 0, 0),
            (25, 60, 28, 70, ".", 2, 0, 1),
            (32, 60, 55, 70, "Qué", 2, 0, 2),
            (59, 60, 95, 70, "aprendemos?", 2, 0, 3),
            (220, 40, 225, 50, "2", 3, 0, 0),
            (229, 40, 275, 50, "Segundo", 3, 0, 1),
            (279, 40, 320, 50, "párrafo", 3, 0, 2),
            (220, 60, 225, 70, "2", 4, 0, 0),
            (225, 60, 228, 70, ".", 4, 0, 1),
            (232, 60, 250, 70, "Otra", 4, 0, 2),
            (254, 60, 290, 70, "pregunta?", 4, 0, 3),
        ]

        result = read_page_with_ocr(FakePage(words))

        lines = result["text"].splitlines()
        self.assertLess(lines.index("1 Primer párrafo"), lines.index("2 Segundo párrafo"))
        self.assertIn("1. ¿Qué aprendemos?", lines)
        self.assertIn("2. ¿Otra pregunta?", lines)
        self.assertEqual(lines.count("Respuesta"), 2)

    @patch("app.readers.ocr_reader.fitz.get_tessdata", return_value="tessdata")
    def test_repairs_ocr_header_and_question_numbering(self, get_tessdata):
        words = [
            (100, 10, 135, 20, "Título", 0, 0, 0),
            (139, 10, 170, 20, "real", 0, 0, 1),
            (100, 25, 125, 35, "“Cita", 1, 0, 0),
            (129, 25, 170, 35, "bíblica”", 1, 0, 1),
            (20, 40, 70, 50, "CANCIÓN", 2, 0, 0),
            (74, 40, 85, 50, "56", 2, 0, 1),
            (20, 55, 40, 65, "Vive", 3, 0, 0),
            (44, 55, 70, 65, "feliz", 3, 0, 1),
            (20, 70, 50, 80, "TEMA", 4, 0, 0),
            (20, 90, 25, 100, "9", 5, 0, 0),
            (25, 90, 28, 100, ",", 5, 0, 1),
            (32, 90, 55, 100, "Qué", 5, 0, 2),
            (59, 90, 90, 100, "hacer?", 5, 0, 3),
        ]

        result = read_page_with_ocr(FakePage(words))
        lines = result["text"].splitlines()

        self.assertEqual(lines[0], "CANCIÓN 56 Vive feliz")
        self.assertEqual(lines[1], "Título real")
        self.assertEqual(lines[2], "“Cita bíblica”")
        self.assertIn("9. ¿Qué hacer?", lines)

    @patch(
        "app.readers.ocr_reader.fitz.get_tessdata",
        side_effect=RuntimeError("Tesseract missing"),
    )
    def test_reports_unavailable_ocr(self, get_tessdata):
        with self.assertRaisesRegex(OcrUnavailableError, "OCR no está disponible"):
            read_page_with_ocr(FakePage())

        get_tessdata.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
