import tempfile
import unittest
from pathlib import Path

from docx import Document

from app.exporters.word_exporter import (
    WordExportError,
    export_generated_article_to_docx,
)
from app.generation.generated_article import (
    GeneratedArticle,
    GeneratedBox,
    GeneratedIntroduction,
    GeneratedQuestion,
    GeneratedSection,
)
from app.models import Project
from app.persistence.generated_article_repository import (
    JsonGeneratedArticleRepository,
)


class GeneratedArticleWordExporterTests(unittest.TestCase):
    @staticmethod
    def article() -> GeneratedArticle:
        return GeneratedArticle(
            title="Artículo exportado",
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
                ],
            ),
            sections=[
                GeneratedSection(
                    subtitle="Primera sección",
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
                            title="Recuadro",
                            explanation="Explicación del recuadro",
                            linked_paragraph=2,
                        )
                    ],
                )
            ],
            review_questions=["¿Qué aprendimos?"],
        )

    def test_exports_complete_generated_article_without_creating_master(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = Project(
                name="Proyecto exportado",
                root=temporary,
            )
            JsonGeneratedArticleRepository(temporary).save(self.article())

            output = export_generated_article_to_docx(project)

            self.assertEqual(
                output,
                Path(temporary) / "salidas" / "CONTENIDO_GENERADO.docx",
            )
            self.assertTrue(output.is_file())
            self.assertFalse(
                (Path(temporary) / "trabajo" / "master.json").exists()
            )

            document = Document(output)
            text = "\n".join(
                paragraph.text for paragraph in document.paragraphs
            )

        expected_texts = [
            "Artículo exportado",
            "Introducción fuente",
            "¿Pregunta inicial?",
            "Respuesta inicial",
            "Aplicación inicial",
            "Primera sección",
            "Transición de prueba",
            "¿Pregunta de sección?",
            "Respuesta de sección",
            "Aplicación de sección",
            "Resumen de la sección",
            "Recuadro",
            "Explicación del recuadro",
            "Preguntas de repaso",
            "¿Qué aprendimos?",
        ]
        for expected in expected_texts:
            with self.subTest(text=expected):
                self.assertIn(expected, text)

    def test_does_not_modify_existing_master(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = Project(
                name="Proyecto con MASTER",
                root=temporary,
            )
            work = Path(temporary) / "trabajo"
            work.mkdir(parents=True)
            master_path = work / "master.json"
            original_master = '{"title": "MASTER legacy"}'
            master_path.write_text(original_master, encoding="utf-8")
            JsonGeneratedArticleRepository(temporary).save(self.article())

            export_generated_article_to_docx(project)

            self.assertEqual(
                master_path.read_text(encoding="utf-8"),
                original_master,
            )

    def test_rejects_missing_generated_article(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = Project(
                name="Proyecto sin contenido",
                root=temporary,
            )

            with self.assertRaisesRegex(
                WordExportError,
                "articulo_generado.json",
            ):
                export_generated_article_to_docx(project)


if __name__ == "__main__":
    unittest.main()
