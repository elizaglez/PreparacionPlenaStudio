import json
import tempfile
import unittest
from pathlib import Path

from app.logging.generation_log import GenerationLog


class GenerationLogTests(unittest.TestCase):
    def test_records_generation_entry(self):
        with tempfile.TemporaryDirectory() as directory:
            log = GenerationLog(directory)
            path = log.record(
                question_number=1,
                question="¿Qué aprendemos?",
                model="test-model",
                instructions="Reglas",
                input_text="Contexto",
                output={"answer": "Respuesta"},
                duration_seconds=1.25,
                operation="generate",
            )

            self.assertTrue(path.is_file())
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["question_number"], 1)
            self.assertEqual(data["model"], "test-model")
            self.assertEqual(data["operation"], "generate")


if __name__ == "__main__":
    unittest.main()
