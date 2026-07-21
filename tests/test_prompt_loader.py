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


if __name__ == "__main__":
    unittest.main()
