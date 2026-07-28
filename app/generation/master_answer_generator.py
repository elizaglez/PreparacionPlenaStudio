from __future__ import annotations

import time

from app.ai import OpenAIEditor
from app.config import ROOT_DIR
from app.context import ContextBuilder, QuestionContext
from app.logging import GenerationLog
from app.models import Project
from app.models.master import MasterAnswer
from app.pipeline import PipelineEngine, PipelineStage, PipelineStateStore
from app.pipeline.execution import PipelineExecution
from app.prompts import PromptLoader


class MasterGenerationError(RuntimeError):
    pass


PIPELINE_STAGES = (
    PipelineStage(
        key="answer",
        label="Respuesta principal",
        output_field="answer",
        required=True,
    ),
    PipelineStage(
        key="scripture_explanation",
        label="Explicación bíblica",
        output_field="scripture_explanation",
        dependencies=("answer",),
    ),
    PipelineStage(
        key="comparison",
        label="Comparación",
        output_field="comparison",
        dependencies=("answer",),
    ),
    PipelineStage(
        key="application",
        label="Aplicación",
        output_field="application",
        dependencies=("answer",),
    ),
    PipelineStage(
        key="image_note",
        label="Nota de imagen",
        output_field="image_note",
        dependencies=("answer",),
    ),
)

STAGE_INSTRUCTIONS = {
    "answer": (
        "Redacta una respuesta corta, directa y conversacional basada solo en "
        "los párrafos y textos suministrados."
    ),
    "scripture_explanation": (
        "Explica brevemente cómo la cita bíblica apoya la respuesta. Déjala "
        "vacía cuando no sea necesaria o no haya base suficiente."
    ),
    "comparison": (
        "Incluye una comparación sencilla únicamente cuando ayude de verdad a "
        "entender la idea. De lo contrario devuelve una cadena vacía."
    ),
    "application": (
        "Da una aplicación práctica, breve y fiel a las fuentes. No especules "
        "ni añadas reglas doctrinales."
    ),
    "image_note": (
        "Explica la imagen únicamente si los párrafos o el audio aportan esa "
        "explicación. Si no hay base, devuelve una cadena vacía."
    ),
}


def _prompt_loader() -> PromptLoader:
    return PromptLoader(ROOT_DIR / "prompts")


def _answer_from_result(section: dict, result: dict) -> MasterAnswer:
    question = str(section.get("question", "")).strip()
    if not question:
        raise MasterGenerationError(
            "Una sección del artículo no contiene pregunta."
        )

    answer = str(result.get("answer", "")).strip()
    if not answer:
        raise MasterGenerationError(
            f"La IA no produjo una respuesta válida para: {question}"
        )

    notes = result.get("source_notes", [])
    if not isinstance(notes, list):
        notes = []

    return MasterAnswer(
        number=int(section.get("number", 0)),
        question=question,
        answer=answer,
        paragraph_numbers=[
            int(value)
            for value in section.get("paragraph_numbers", [])
            if str(value).isdigit()
        ],
        scriptures=[
            str(value)
            for value in section.get("scripture_references", [])
        ],
        scripture_explanation=str(
            result.get("scripture_explanation", "")
        ).strip(),
        comparison=str(result.get("comparison", "")).strip(),
        application=str(result.get("application", "")).strip(),
        image_note=str(result.get("image_note", "")).strip(),
        source_notes=[
            str(value).strip()
            for value in notes
            if str(value).strip()
        ],
    )


def _stage_input(
    context: QuestionContext,
    stage_key: str,
    values: dict[str, str],
) -> str:
    return _prompt_loader().render(
        "pipeline_stage",
        {
            "title": context.article_title,
            "introduction": context.article_introduction or "No disponible.",
            "heading": context.heading or "No disponible.",
            "previous_question": context.previous_question or "No disponible.",
            "question": context.question,
            "next_question": context.next_question or "No disponible.",
            "paragraphs": context.paragraph_text or "No disponibles.",
            "references": ", ".join(context.scripture_references) or "Ninguna.",
            "bible_context": context.bible_context or "No disponible.",
            "answer": values.get("answer", "No disponible."),
            "scripture_explanation": values.get(
                "scripture_explanation", "No disponible."
            ),
            "comparison": values.get("comparison", "No disponible."),
            "application": values.get("application", "No disponible."),
            "stage_instruction": STAGE_INSTRUCTIONS[stage_key],
        },
    )


def _generate_one(
    *,
    project: Project,
    editor: OpenAIEditor,
    instructions: str,
    article: dict,
    context_builder: ContextBuilder,
    section_index: int,
    model: str,
    log: GenerationLog,
    operation: str,
    state_store: PipelineStateStore | None = None,
    only_stage: str | None = None,
    existing_answer: dict | None = None,
) -> MasterAnswer:
    section = article["sections"][section_index]
    context = context_builder.build(section_index)
    initial_values = {
        key: str((existing_answer or {}).get(key, "")).strip()
        for key in (
            "answer",
            "scripture_explanation",
            "comparison",
            "application",
            "image_note",
        )
    }

    def execute(stage: PipelineStage, execution: PipelineExecution):
        input_text = _stage_input(context, stage.key, execution.values)
        started = time.perf_counter()
        result = editor.generate_json(
            instructions=instructions,
            input_text=input_text,
        )
        duration = time.perf_counter() - started
        raw_value = result.get(
            "value",
            result.get(stage.output_field, ""),
        )
        value = "" if raw_value is None else str(raw_value).strip()
        notes = result.get("source_notes", [])
        if not isinstance(notes, list):
            notes = []
        log.record(
            question_number=int(section.get("number", 0)),
            question=context.question,
            model=model,
            instructions=instructions,
            input_text=input_text,
            output=result,
            duration_seconds=duration,
            operation=f"{operation}:{stage.key}",
            warnings=[],
        )
        return value, notes

    engine = PipelineEngine(
        PIPELINE_STAGES,
        execute,
        state_store=state_store,
    )
    results = engine.run(
        project,
        question_number=int(section.get("number", 0)),
        question=context.question,
        initial_values=initial_values,
        only_stage=only_stage,
    )

    combined = dict(initial_values)
    source_notes = list((existing_answer or {}).get("source_notes", []))
    for stage_key, result in results.items():
        combined[stage_key] = result.value
        source_notes.extend(result.source_notes)

    payload = {
        "answer": combined.get("answer", ""),
        "scripture_explanation": combined.get("scripture_explanation", ""),
        "comparison": combined.get("comparison", ""),
        "application": combined.get("application", ""),
        "image_note": combined.get("image_note", ""),
        "source_notes": list(dict.fromkeys(source_notes)),
    }
    return _answer_from_result(section, payload)
