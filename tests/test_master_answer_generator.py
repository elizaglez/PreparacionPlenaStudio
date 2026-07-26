import unittest
from unittest.mock import patch

from app.context import QuestionContext
from app.generation.master_answer_generator import (
    PIPELINE_STAGES,
    _generate_one,
)
from app.models import Project
from app.pipeline import PipelineError


class FakeContextBuilder:
    def __init__(self, context):
        self.context = context
        self.calls = []

    def build(self, section_index):
        self.calls.append(section_index)
        return self.context


class FakeEditor:
    def __init__(self, results):
        self.results = list(results)
        self.calls = []

    def generate_json(self, *, instructions, input_text):
        self.calls.append(
            {"instructions": instructions, "input_text": input_text}
        )
        return self.results[len(self.calls) - 1]


class FakeGenerationLog:
    def __init__(self):
        self.records = []

    def record(self, **kwargs):
        self.records.append(kwargs)


class FakePromptLoader:
    def __init__(self):
        self.calls = []

    def render(self, name, values):
        snapshot = dict(values)
        self.calls.append({"name": name, "values": snapshot})
        return f"prompt-{len(self.calls)}"


class MasterAnswerGeneratorTests(unittest.TestCase):
    def setUp(self):
        self.project = Project(name="Proyecto de prueba")
        self.article = {
            "title": "Artículo",
            "sections": [
                {
                    "number": 3,
                    "question": "¿Qué aprendemos?",
                    "paragraph_numbers": [5, 6],
                    "scripture_references": ["Juan 3:16"],
                }
            ],
        }
        self.context = QuestionContext(
            article_title="Artículo",
            article_introduction="Introducción",
            question_number=3,
            question="¿Qué aprendemos?",
            paragraph_text="Párrafo 5: Texto fuente.",
            scripture_references=["Juan 3:16"],
            bible_context="Juan 3:16 Porque Dios amó al mundo.",
            heading="Tema",
        )

    @staticmethod
    def stage_results(notes=None):
        values = [
            "Respuesta principal",
            "Explicación bíblica",
            "Comparación",
            "Aplicación",
            "Nota de imagen",
        ]
        notes = notes or [[] for _ in values]
        return [
            {"value": value, "source_notes": stage_notes}
            for value, stage_notes in zip(values, notes)
        ]

    def generate(
        self,
        editor,
        log,
        prompt_loader,
        *,
        operation="generate",
        only_stage=None,
        existing_answer=None,
    ):
        context_builder = FakeContextBuilder(self.context)
        with patch(
            "app.generation.master_answer_generator._prompt_loader",
            return_value=prompt_loader,
        ):
            answer = _generate_one(
                project=self.project,
                editor=editor,
                instructions="Instrucciones del sistema",
                article=self.article,
                context_builder=context_builder,
                section_index=0,
                model="test-model",
                log=log,
                operation=operation,
                only_stage=only_stage,
                existing_answer=existing_answer,
            )
        return answer, context_builder

    def test_generates_all_pipeline_stages(self):
        editor = FakeEditor(self.stage_results())
        log = FakeGenerationLog()
        prompts = FakePromptLoader()

        answer, context_builder = self.generate(editor, log, prompts)

        self.assertEqual(context_builder.calls, [0])
        self.assertEqual(len(editor.calls), len(PIPELINE_STAGES))
        self.assertEqual(
            [call["name"] for call in prompts.calls],
            ["pipeline_stage"] * len(PIPELINE_STAGES),
        )
        self.assertEqual(answer.number, 3)
        self.assertEqual(answer.question, "¿Qué aprendemos?")
        self.assertEqual(answer.answer, "Respuesta principal")
        self.assertEqual(answer.scripture_explanation, "Explicación bíblica")
        self.assertEqual(answer.comparison, "Comparación")
        self.assertEqual(answer.application, "Aplicación")
        self.assertEqual(answer.image_note, "Nota de imagen")
        self.assertEqual(answer.paragraph_numbers, [5, 6])
        self.assertEqual(answer.scriptures, ["Juan 3:16"])
        self.assertEqual(
            prompts.calls[1]["values"]["answer"],
            "Respuesta principal",
        )

    def test_logs_operation_for_each_stage(self):
        editor = FakeEditor(self.stage_results())
        log = FakeGenerationLog()
        prompts = FakePromptLoader()

        self.generate(editor, log, prompts, operation="generate")

        self.assertEqual(
            [record["operation"] for record in log.records],
            [f"generate:{stage.key}" for stage in PIPELINE_STAGES],
        )
        for record in log.records:
            self.assertEqual(record["question_number"], 3)
            self.assertEqual(record["question"], "¿Qué aprendemos?")
            self.assertEqual(record["model"], "test-model")
            self.assertEqual(record["instructions"], "Instrucciones del sistema")
            self.assertGreaterEqual(record["duration_seconds"], 0)
            self.assertEqual(record["warnings"], [])

    def test_only_stage_preserves_existing_values(self):
        existing = {
            "answer": "Respuesta existente",
            "scripture_explanation": "Explicación existente",
            "comparison": "Comparación existente",
            "application": "Aplicación anterior",
            "image_note": "Nota existente",
            "source_notes": ["Fuente existente"],
        }
        editor = FakeEditor(
            [{"value": "Aplicación regenerada", "source_notes": ["Fuente nueva"]}]
        )
        log = FakeGenerationLog()
        prompts = FakePromptLoader()

        answer, _ = self.generate(
            editor,
            log,
            prompts,
            operation="regenerate_stage",
            only_stage="application",
            existing_answer=existing,
        )

        self.assertEqual(len(editor.calls), 1)
        self.assertEqual(log.records[0]["operation"], "regenerate_stage:application")
        self.assertEqual(answer.answer, "Respuesta existente")
        self.assertEqual(answer.scripture_explanation, "Explicación existente")
        self.assertEqual(answer.comparison, "Comparación existente")
        self.assertEqual(answer.application, "Aplicación regenerada")
        self.assertEqual(answer.image_note, "Nota existente")
        self.assertEqual(prompts.calls[0]["values"]["answer"], "Respuesta existente")

    def test_deduplicates_source_notes_preserving_order(self):
        notes = [
            ["Fuente repetida", "Fuente B"],
            ["Fuente C", "Fuente B"],
            [],
            [],
            [],
        ]
        editor = FakeEditor(self.stage_results(notes))
        log = FakeGenerationLog()
        prompts = FakePromptLoader()

        answer, _ = self.generate(
            editor,
            log,
            prompts,
            existing_answer={
                "source_notes": ["Fuente A", "Fuente repetida"],
            },
        )

        self.assertEqual(
            answer.source_notes,
            ["Fuente A", "Fuente repetida", "Fuente B", "Fuente C"],
        )

    def test_rejects_empty_required_answer(self):
        editor = FakeEditor([{"value": "   ", "source_notes": []}])
        log = FakeGenerationLog()
        prompts = FakePromptLoader()

        with self.assertRaisesRegex(PipelineError, "devolvió contenido vacío"):
            self.generate(editor, log, prompts)

        self.assertEqual(len(editor.calls), 1)
        self.assertEqual(len(log.records), 1)
        self.assertEqual(log.records[0]["operation"], "generate:answer")


if __name__ == "__main__":
    unittest.main()
