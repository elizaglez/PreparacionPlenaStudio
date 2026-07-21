import unittest

from app.validation.master_validator import validate_master


class MasterValidatorTests(unittest.TestCase):
    def setUp(self):
        self.article = {
            "sections": [
                {
                    "number": 1,
                    "question": "¿Qué aprendemos?",
                    "scripture_references": ["Juan 3:16"],
                }
            ]
        }

    def test_valid_master(self):
        master = {
            "answers": [
                {
                    "number": 1,
                    "question": "¿Qué aprendemos?",
                    "answer": "Aprendemos a mostrar amor.",
                    "scriptures": ["Juan 3:16"],
                }
            ]
        }
        report = validate_master(self.article, master)
        self.assertTrue(report.valid)

    def test_changed_question_is_error(self):
        master = {
            "answers": [
                {
                    "number": 1,
                    "question": "¿Qué debemos hacer?",
                    "answer": "Una respuesta.",
                    "scriptures": ["Juan 3:16"],
                }
            ]
        }
        report = validate_master(self.article, master)
        self.assertFalse(report.valid)
        self.assertTrue(
            any(issue.code == "QUESTION_CHANGED" for issue in report.issues)
        )

    def test_missing_scripture_is_warning(self):
        master = {
            "answers": [
                {
                    "number": 1,
                    "question": "¿Qué aprendemos?",
                    "answer": "Una respuesta.",
                    "scriptures": [],
                }
            ]
        }
        report = validate_master(self.article, master)
        self.assertTrue(report.valid)
        self.assertTrue(
            any(issue.code == "SCRIPTURES_LOST" for issue in report.issues)
        )


if __name__ == "__main__":
    unittest.main()
