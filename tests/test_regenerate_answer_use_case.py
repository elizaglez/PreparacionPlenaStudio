import json
import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from app.models import Project
from app.models.master import MasterAnswer
from app.use_cases.regenerate_answer import RegenerateAnswerUseCase


class UseCaseError(RuntimeError):
    pass


class FakeReport:
    def __init__(self, valid=True):
        self.valid = valid

    def to_dict(self):
        return {"valid": self.valid, "issues": []}


class RegenerateAnswerUseCaseTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.work_dir = self.root / "trabajo"
        self.work_dir.mkdir()
        self.article = {
            "title": "Artículo",
            "sections": [
                {"number": 1, "question": "¿Pregunta uno?"},
                {"number": 2, "question": "¿Pregunta dos?"},
            ],
        }
        self.master = {
            "title": "MASTER",
            "answers": [
                {"number": 1, "question": "¿Pregunta uno?", "answer": "Anterior"},
                {"number": 2, "question": "¿Pregunta dos?", "answer": "Conservar"},
            ],
            "generated_at": "anterior",
        }
        self.write_json("articulo.json", self.article)
        self.write_json("master.json", self.master)
        self.project = Project(name="Proyecto", root=str(self.root))
        self.fixed_now = datetime(2026, 2, 3, 4, 5, 6, tzinfo=timezone.utc)

    def write_json(self, name, value):
        (self.work_dir / name).write_text(
            json.dumps(value, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def load_json(path):
        return json.loads(path.read_text(encoding="utf-8"))

    def make_use_case(self, validator, calls):
        def generate_one(**kwargs):
            calls.append(kwargs)
            return MasterAnswer(
                number=1,
                question="¿Pregunta uno?",
                answer="Regenerada",
                application="Aplicación nueva",
            )

        return RegenerateAnswerUseCase(
            load_json=self.load_json,
            methodology_instructions=lambda value: "Instrucciones",
            generate_one=generate_one,
            error_type=UseCaseError,
            settings_loader=lambda: {"openai_model": "test-model"},
            methodology_loader=lambda: {"name": "Método"},
            editor_factory=lambda model: ("editor", model),
            context_builder_factory=lambda article, bible: (article, bible),
            generation_log_factory=lambda root: ("log", root),
            pipeline_state_factory=lambda root: ("state", root),
            validator=validator,
            now=lambda: self.fixed_now,
        )

    def test_replaces_existing_answer(self):
        calls = []
        use_case = self.make_use_case(
            lambda article, master: FakeReport(valid=True),
            calls,
        )

        replacement = use_case.execute(self.project, 1)

        self.assertEqual(replacement["answer"], "Regenerada")
        self.assertEqual(calls[0]["operation"], "regenerate")
        self.assertEqual(calls[0]["existing_answer"]["answer"], "Anterior")
        saved = self.load_json(self.work_dir / "master.json")
        self.assertEqual(saved["answers"][0]["answer"], "Regenerada")
        self.assertEqual(saved["answers"][1]["answer"], "Conservar")
        self.assertTrue((self.work_dir / "master_validacion.json").is_file())

    def test_rejects_unknown_question(self):
        calls = []
        use_case = self.make_use_case(
            lambda article, master: FakeReport(valid=True),
            calls,
        )

        with self.assertRaisesRegex(UseCaseError, "No existe la pregunta número 99"):
            use_case.execute(self.project, 99)

        self.assertEqual(calls, [])

    def test_validation_failure_writes_report_without_overwriting_master(self):
        calls = []
        original = (self.work_dir / "master.json").read_text(encoding="utf-8")
        use_case = self.make_use_case(
            lambda article, master: FakeReport(valid=False),
            calls,
        )

        with self.assertRaisesRegex(
            UseCaseError,
            "La respuesta regenerada no superó la validación",
        ):
            use_case.execute(self.project, 1)

        self.assertTrue((self.work_dir / "master_validacion.json").is_file())
        self.assertEqual(
            (self.work_dir / "master.json").read_text(encoding="utf-8"),
            original,
        )

    def test_appends_missing_answer_in_numeric_order(self):
        self.write_json(
            "master.json",
            {
                "title": "MASTER",
                "answers": [self.master["answers"][1]],
                "generated_at": "anterior",
            },
        )
        calls = []
        use_case = self.make_use_case(
            lambda article, master: FakeReport(valid=True),
            calls,
        )

        replacement = use_case.execute(self.project, 1)

        self.assertEqual(calls[0]["operation"], "regenerate")
        self.assertEqual(calls[0]["existing_answer"], {})
        self.assertEqual(replacement["number"], 1)
        saved = self.load_json(self.work_dir / "master.json")
        self.assertEqual(
            [answer["number"] for answer in saved["answers"]],
            [1, 2],
        )
        self.assertEqual(saved["answers"][0]["answer"], "Regenerada")
        self.assertEqual(saved["answers"][1]["answer"], "Conservar")
        self.assertTrue((self.work_dir / "master_validacion.json").is_file())


if __name__ == "__main__":
    unittest.main()
