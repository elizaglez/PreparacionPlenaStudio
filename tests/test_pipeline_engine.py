import tempfile
import unittest
from pathlib import Path

from app.models import Project
from app.pipeline import (
    PipelineEngine,
    PipelineError,
    PipelineStage,
    PipelineStateStore,
    StageStatus,
)
from app.pipeline.execution import PipelineExecution


class PipelineEngineTests(unittest.TestCase):
    def setUp(self):
        self.project = Project(name="Proyecto de prueba")
        self.stages = (
            PipelineStage("answer", "Respuesta", "answer", required=True),
            PipelineStage(
                "application",
                "Aplicación",
                "application",
                dependencies=("answer",),
            ),
        )

    def test_runs_stages_in_order_and_persists_state(self):
        calls = []

        def executor(stage, execution: PipelineExecution):
            calls.append(stage.key)
            if stage.key == "answer":
                return "Respuesta breve", ["Párrafo 1"]
            return f"Aplicación de {execution.values['answer']}", []

        with tempfile.TemporaryDirectory() as tmp:
            store = PipelineStateStore(tmp)
            engine = PipelineEngine(self.stages, executor, state_store=store)
            results = engine.run(
                self.project,
                question_number=1,
                question="¿Pregunta?",
            )

            self.assertEqual(calls, ["answer", "application"])
            self.assertEqual(results["answer"].status, StageStatus.COMPLETED)
            self.assertTrue(store.path.is_file())
            saved = store.load()["questions"]["1"]["stages"]
            self.assertEqual(saved["application"]["status"], "completed")

    def test_regenerates_only_selected_stage(self):
        calls = []

        def executor(stage, execution: PipelineExecution):
            calls.append(stage.key)
            return "Nueva aplicación", []

        engine = PipelineEngine(self.stages, executor)
        results = engine.run(
            self.project,
            question_number=2,
            question="¿Pregunta?",
            initial_values={"answer": "Respuesta existente"},
            only_stage="application",
        )
        self.assertEqual(calls, ["application"])
        self.assertEqual(results["application"].value, "Nueva aplicación")

    def test_dependency_is_required_for_individual_stage(self):
        engine = PipelineEngine(
            self.stages,
            lambda stage, execution: ("x", []),
        )
        with self.assertRaises(PipelineError):
            engine.run(
                self.project,
                question_number=3,
                question="¿Pregunta?",
                only_stage="application",
            )


if __name__ == "__main__":
    unittest.main()
