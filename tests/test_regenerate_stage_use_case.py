import json
import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from app.models import Project
from app.models.master import MasterAnswer
from app.pipeline import PipelineStage
from app.use_cases.regenerate_stage import RegenerateStageUseCase


class UseCaseError(RuntimeError):
    pass


class FakeReport:
    def __init__(self, valid=True):
        self.valid = valid

    def to_dict(self):
        return {"valid": self.valid, "issues": []}


class RegenerateStageUseCaseTests(unittest.TestCase):
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
                {
                    "number": 1,
                    "question": "¿Pregunta uno?",
                    "answer": "Respuesta existente",
                    "application": "Aplicación anterior",
                }
            ],
            "generated_at": "anterior",
        }
        self.write_json("articulo.json", self.article)
        self.write_json("master.json", self.master)
        self.project = Project(name="Proyecto", root=str(self.root))
        self.fixed_now = datetime(2026, 3, 4, 5, 6, 7, tzinfo=timezone.utc)
        self.stages = (
            PipelineStage("answer", "Respuesta", "answer", required=True),
            PipelineStage(
                "application",
                "Aplicación",
                "application",
                dependencies=("answer",),
            ),
        )

    def write_json(self, name, value):
        (self.work_dir / name).write_text(
            json.dumps(value, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def load_json(path):
        return json.loads(path.read_text(encoding="utf-8"))

    def make_use_case(self, validator, calls, load_json=None):
        def generate_one(**kwargs):
            calls.append(kwargs)
            return MasterAnswer(
                number=1,
                question="¿Pregunta uno?",
                answer="Respuesta existente",
                application="Aplicación regenerada",
            )

        return RegenerateStageUseCase(
            pipeline_stages=self.stages,
            load_json=load_json or self.load_json,
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

    def test_regenerates_selected_stage(self):
        calls = []
        use_case = self.make_use_case(
            lambda article, master: FakeReport(valid=True),
            calls,
        )

        replacement = use_case.execute(self.project, 1, "application")

        self.assertEqual(calls[0]["operation"], "regenerate_stage")
        self.assertEqual(calls[0]["only_stage"], "application")
        self.assertEqual(calls[0]["existing_answer"]["answer"], "Respuesta existente")
        self.assertEqual(replacement["application"], "Aplicación regenerada")
        self.assertEqual(replacement["status"], "regenerated")
        saved = self.load_json(self.work_dir / "master.json")
        self.assertEqual(saved["answers"][0], replacement)
        self.assertTrue((self.work_dir / "master_validacion.json").is_file())

    def test_rejects_unknown_stage_before_loading_files(self):
        calls = []

        def unexpected_load(path):
            self.fail("No debe cargar JSON para una etapa inválida")

        use_case = self.make_use_case(
            lambda article, master: FakeReport(valid=True),
            calls,
            load_json=unexpected_load,
        )

        with self.assertRaisesRegex(UseCaseError, "Etapa desconocida: unknown"):
            use_case.execute(self.project, 1, "unknown")

        self.assertEqual(calls, [])

    def test_rejects_answer_missing_from_master(self):
        calls = []
        use_case = self.make_use_case(
            lambda article, master: FakeReport(valid=True),
            calls,
        )

        with self.assertRaisesRegex(
            UseCaseError,
            "El MASTER no contiene la pregunta número 2",
        ):
            use_case.execute(self.project, 2, "application")

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
            "La etapa regenerada no superó la validación del MASTER",
        ):
            use_case.execute(self.project, 1, "application")

        self.assertTrue((self.work_dir / "master_validacion.json").is_file())
        self.assertEqual(
            (self.work_dir / "master.json").read_text(encoding="utf-8"),
            original,
        )


if __name__ == "__main__":
    unittest.main()
