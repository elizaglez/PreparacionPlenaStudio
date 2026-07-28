import tempfile
import unittest
from pathlib import Path

from app.prompts.prompt_loader import PromptLoader, PromptRenderError


class PromptLoaderTests(unittest.TestCase):
    def test_renders_prompt(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "answer.md"
            path.write_text("Pregunta: $question", encoding="utf-8")
            loader = PromptLoader(Path(directory))
            self.assertEqual(
                loader.render("answer", {"question": "¿Qué aprendemos?"}),
                "Pregunta: ¿Qué aprendemos?",
            )

    def test_missing_value_raises(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "answer.md"
            path.write_text("$question", encoding="utf-8")
            loader = PromptLoader(Path(directory))
            with self.assertRaises(PromptRenderError):
                loader.render("answer", {})

    def test_renders_real_pipeline_stage_prompt(self):
        prompt_dir = Path(__file__).resolve().parents[1] / "prompts"
        loader = PromptLoader(prompt_dir)
        values = {
            "title": "Título real",
            "introduction": "Introducción real",
            "heading": "Subtítulo real",
            "previous_question": "Pregunta anterior real",
            "question": "¿Pregunta real?",
            "next_question": "Pregunta siguiente real",
            "paragraphs": "Párrafos reales",
            "references": "Referencias reales",
            "bible_context": "Contexto bíblico real",
            "answer": "Respuesta real",
            "scripture_explanation": "Explicación real",
            "comparison": "Comparación real",
            "application": "Aplicación real",
            "stage_instruction": "Instrucción real",
        }

        rendered = loader.render("pipeline_stage", values)

        for value in values.values():
            self.assertIn(value, rendered)
        self.assertNotRegex(rendered, r"\{[a-z_]+\}")
        self.assertIn(
            '{\n  "value": "texto de la etapa; puede ser vacío solo si no es útil",',
            rendered,
        )
        self.assertIn(
            '"source_notes": ["fuentes concretas usadas"]\n}',
            rendered,
        )


if __name__ == "__main__":
    unittest.main()
