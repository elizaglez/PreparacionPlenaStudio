import unittest

from app.master_generator import (
    _answer_from_result,
    _methodology_instructions,
)


class MasterGeneratorTests(unittest.TestCase):
    def test_preserves_exact_question(self):
        section = {
            "number": 3,
            "question": "¿Qué aprendemos de este ejemplo?",
            "paragraph_numbers": [5, 6],
            "scripture_references": ["Juan 3:16"],
        }
        result = {
            "answer": "Aprendemos a actuar con amor.",
            "source_notes": ["Párrafos 5 y 6"],
        }
        answer = _answer_from_result(section, result)
        self.assertEqual(answer.question, section["question"])
        self.assertEqual(answer.paragraph_numbers, [5, 6])

    def test_methodology_forbids_speculation(self):
        instructions = _methodology_instructions(
            {"principles": ["No se permite especulación."]}
        )
        self.assertIn("No se permite especulación", instructions)


if __name__ == "__main__":
    unittest.main()
