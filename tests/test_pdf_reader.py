from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from app.readers.pdf_reader import PdfReadError, read_pdf
from app.readers.ocr_reader import OcrUnavailableError


class FakePage:
    def __init__(self, text=""):
        self.text = text

    def get_text(self, kind):
        if kind == "text":
            return self.text
        return []


class FakeDocument:
    def __init__(self, pages):
        self.pages = pages
        self.page_count = len(pages)
        self.metadata = {"title": "Revista", "author": "Autor"}
        self.closed = False

    def __iter__(self):
        return iter(self.pages)

    def close(self):
        self.closed = True


class PdfReaderTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / "revista.pdf"
        self.path.write_bytes(b"%PDF-1.4")

    @patch("app.readers.pdf_reader.read_page_with_ocr")
    @patch("app.readers.pdf_reader.fitz.open")
    def test_preserves_native_extraction_without_ocr(self, open_pdf, read_ocr):
        document = FakeDocument(
            [FakePage("Texto nativo suficientemente extenso para analizar la página.")]
        )
        open_pdf.return_value = document

        result = read_pdf(self.path)

        read_ocr.assert_not_called()
        self.assertIn("Texto nativo", result["text"])
        self.assertEqual(result["pages"][0]["page_number"], 1)
        self.assertTrue(document.closed)

    @patch("app.readers.pdf_reader.read_page_with_ocr")
    @patch("app.readers.pdf_reader.fitz.open")
    def test_uses_ocr_when_native_pdf_has_no_text(self, open_pdf, read_ocr):
        document = FakeDocument([FakePage(), FakePage()])
        open_pdf.return_value = document
        read_ocr.side_effect = [
            {
                "text": (
                    "1 Primer párrafo reconocido con suficiente contenido.\n"
                    "1. ¿Qué aprendemos del primer párrafo?\nRespuesta"
                ),
                "blocks": [],
            },
            {
                "text": (
                    "2 Segundo párrafo reconocido con suficiente contenido.\n"
                    "2. ¿Qué aprendemos del segundo párrafo?\nRespuesta"
                ),
                "blocks": [],
            },
        ]

        result = read_pdf(self.path)

        self.assertEqual(read_ocr.call_count, 2)
        self.assertEqual(result["page_count"], 2)
        self.assertEqual(
            [page["page_number"] for page in result["pages"]],
            [1, 2],
        )
        self.assertIn("1 Primer párrafo reconocido", result["text"])
        self.assertIn("2 Segundo párrafo reconocido", result["text"])
        self.assertIn("1. ¿Qué aprendemos", result["text"])
        self.assertIn("2. ¿Qué aprendemos", result["text"])
        self.assertTrue(document.closed)

    @patch("app.readers.pdf_reader.read_page_with_ocr")
    @patch("app.readers.pdf_reader.fitz.open")
    def test_reports_when_required_ocr_is_unavailable(self, open_pdf, read_ocr):
        document = FakeDocument([FakePage()])
        open_pdf.return_value = document
        read_ocr.side_effect = OcrUnavailableError("OCR no está disponible.")

        with self.assertRaisesRegex(PdfReadError, "OCR no está disponible"):
            read_pdf(self.path)

        self.assertTrue(document.closed)


if __name__ == "__main__":
    unittest.main()
