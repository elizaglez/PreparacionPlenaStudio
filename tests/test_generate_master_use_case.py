import json
import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from app.models import Project
from app.models.master import MasterAnswer
from app.use_cases.generate_master import GenerateMasterUseCase


class UseCaseError(RuntimeError):
    pass


class FakeReport:
    def __init__(self, valid=True, issues=None):
        self.valid = valid
        self.issues = list(issues or [])

    def to_dict(self):
        return {
            "valid": self.valid,
            "issues": [vars(issue) for issue in self.issues],
        }


class GenerateMasterUseCaseTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.work_dir = self.root / "trabajo"
        self.work_dir.mkdir()
        self.article = {
            "title": "Artículo",
            "introduction": "Introducción",
            "conclusion": "Conclusión",
            "sections": [
                {"number": 1, "question": "¿Pregunta uno?"},
                {"number": 2, "question": "¿Pregunta dos?"},
            ],
            "parser_warnings": ["Advertencia"],
        }
        (self.work_dir / "articulo.json").write_text(
            json.dumps(self.article, ensure_ascii=False),
            encoding="utf-8",
        )
        (self.work_dir / "citas_extraidas.txt").write_text(
            "Juan 3:16",
            encoding="utf-8",
        )
        self.project = Project(name="Proyecto", root=str(self.root))
        self.fixed_now = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)

    @staticmethod
    def load_json(path):
        return json.loads(path.read_text(encoding="utf-8"))

    def make_use_case(self, validator, calls, saved_projects):
        log = SimpleNamespace(log_dir=self.work_dir / "historial_generacion")

        def generate_one(**kwargs):
            calls.append(kwargs)
            section = kwargs["article"]["sections"][kwargs["section_index"]]
            return MasterAnswer(
                number=section["number"],
                question=section["question"],
                answer=f"Respuesta {section['number']}",
            )

        return GenerateMasterUseCase(
            load_json=self.load_json,
            methodology_instructions=lambda value: "Instrucciones",
            generate_one=generate_one,
            emit=lambda callback, value, message: (
                callback(value, message) if callback else None
            ),
            error_type=UseCaseError,
            settings_loader=lambda: {"openai_model": "test-model"},
            methodology_loader=lambda: {"name": "Método de prueba"},
            editor_factory=lambda model: ("editor", model),
            context_builder_factory=lambda article, bible: (article, bible),
            generation_log_factory=lambda root: log,
            pipeline_state_factory=lambda root: ("state", root),
            validator=validator,
            project_saver=saved_projects.append,
            now=lambda: self.fixed_now,
        )

    def test_successful_flow(self):
        calls = []
        saved_projects = []
        progress = []
        use_case = self.make_use_case(
            lambda article, master: FakeReport(valid=True),
            calls,
            saved_projects,
        )

        summary = use_case.execute(
            self.project,
            lambda value, message: progress.append((value, message)),
        )

        self.assertEqual([call["section_index"] for call in calls], [0, 1])
        self.assertTrue(all(call["operation"] == "generate" for call in calls))
        self.assertEqual(summary["answers"], 2)
        self.assertEqual(summary["model"], "test-model")
        self.assertEqual(self.project.status, "master_validado")
        self.assertEqual(saved_projects, [self.project])
        self.assertTrue((self.work_dir / "master.json").is_file())
        self.assertTrue((self.work_dir / "master_validacion.json").is_file())
        master = json.loads(
            (self.work_dir / "master.json").read_text(encoding="utf-8")
        )
        self.assertEqual(len(master["answers"]), 2)
        self.assertEqual(progress[-1][0], 100)

    def test_validation_failure_writes_report_but_not_master(self):
        calls = []
        saved_projects = []
        report = FakeReport(
            valid=False,
            issues=[SimpleNamespace(level="error", message="Respuesta inválida")],
        )
        use_case = self.make_use_case(
            lambda article, master: report,
            calls,
            saved_projects,
        )

        with self.assertRaisesRegex(UseCaseError, "Respuesta inválida"):
            use_case.execute(self.project)

        self.assertTrue((self.work_dir / "master_validacion.json").is_file())
        self.assertFalse((self.work_dir / "master.json").exists())
        self.assertEqual(saved_projects, [])


if __name__ == "__main__":
    unittest.main()
