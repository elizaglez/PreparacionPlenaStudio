from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Callable

from app.ai import OpenAIEditor
from app.config import ROOT_DIR
from app.context import ContextBuilder, QuestionContext
from app.logging import GenerationLog
from app.models import Project
from app.models.master import MasterAnswer, MasterDocument
from app.pipeline import PipelineEngine, PipelineStage, PipelineStateStore
from app.pipeline.execution import PipelineExecution
from app.persistence import save_project
from app.prompts import PromptLoader
from app.storage import load_methodology, load_settings
from app.validation.master_validator import validate_master


class MasterGenerationError(RuntimeError):
    pass


ProgressCallback = Callable[[int, str], None]


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


def _emit(callback: ProgressCallback | None, value: int, message: str) -> None:
    if callback:
        callback(value, message)


def _load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise MasterGenerationError(
            f"No existe {path.name}. Primero analiza y estructura el artículo."
        ) from exc
    except json.JSONDecodeError as exc:
        raise MasterGenerationError(f"{path.name} contiene JSON inválido.") from exc

    if not isinstance(value, dict):
        raise MasterGenerationError(f"{path.name} no tiene la estructura esperada.")
    return value


def _prompt_loader() -> PromptLoader:
    return PromptLoader(ROOT_DIR / "prompts")


def _methodology_instructions(methodology: dict) -> str:
    principles = "\n".join(
        f"- {item}" for item in methodology.get("principles", [])
    )
    return _prompt_loader().render("system", {"principles": principles})


def _build_input(context: QuestionContext) -> str:
    return _prompt_loader().render(
        "answer",
        {
            "title": context.article_title,
            "introduction": context.article_introduction or "No disponible.",
            "heading": context.heading or "No disponible.",
            "previous_question": context.previous_question or "No disponible.",
            "question": context.question,
            "next_question": context.next_question or "No disponible.",
            "paragraphs": context.paragraph_text or "No disponibles.",
            "references": (
                ", ".join(context.scripture_references) or "Ninguna."
            ),
            "bible_context": (
                context.bible_context
                or "No se encontró un fragmento claramente asociado."
            ),
        },
    )


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
        value = str(result.get("value", "")).strip()
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


def generate_master(
    project: Project,
    progress_callback: ProgressCallback | None = None,
) -> dict:
    root = Path(project.root)
    if not root.is_dir():
        raise MasterGenerationError("La carpeta del proyecto no existe.")

    work_dir = root / "trabajo"
    article = _load_json(work_dir / "articulo.json")
    sections = article.get("sections", [])
    if not isinstance(sections, list) or not sections:
        raise MasterGenerationError(
            "articulo.json no contiene preguntas estructuradas."
        )

    bible_path = work_dir / "citas_extraidas.txt"
    bible_text = (
        bible_path.read_text(encoding="utf-8")
        if bible_path.is_file()
        else ""
    )

    settings = load_settings()
    model = settings.get("openai_model", "gpt-5-mini")
    methodology = load_methodology()
    instructions = _methodology_instructions(methodology)
    editor = OpenAIEditor(model=model)
    context_builder = ContextBuilder(article, bible_text)
    generation_log = GenerationLog(root)
    pipeline_state = PipelineStateStore(root)

    answers: list[MasterAnswer] = []
    total = len(sections)

    for index in range(total):
        progress = 5 + int((index / total) * 80)
        _emit(
            progress_callback,
            progress,
            f"Generando respuesta {index + 1} de {total}…",
        )
        answers.append(
            _generate_one(
                editor=editor,
                instructions=instructions,
                article=article,
                context_builder=context_builder,
                section_index=index,
                model=model,
                log=generation_log,
                operation="generate",
                state_store=pipeline_state,
            )
        )

    generated_at = datetime.now().astimezone().isoformat(timespec="seconds")
    master = MasterDocument(
        title=article.get("title", "MASTER"),
        introduction=article.get("introduction", ""),
        answers=answers,
        conclusion=article.get("conclusion", ""),
        methodology=methodology.get("name", "Metodología PPA"),
        model=model,
        generated_at=generated_at,
        warnings=list(article.get("parser_warnings", [])),
    )

    master_data = master.to_dict()

    _emit(progress_callback, 88, "Validando el MASTER…")
    report = validate_master(article, master_data)
    validation_path = work_dir / "master_validacion.json"
    validation_path.write_text(
        json.dumps(report.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    if not report.valid:
        errors = [
            issue.message
            for issue in report.issues
            if issue.level == "error"
        ]
        raise MasterGenerationError(
            "El MASTER no superó la validación:\n- "
            + "\n- ".join(errors)
        )

    _emit(progress_callback, 94, "Guardando master.json…")
    master_path = work_dir / "master.json"
    master_path.write_text(
        json.dumps(master_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    project.status = "master_validado"
    project.updated_at = generated_at
    project.outputs.update(
        {
            "master": "trabajo/master.json",
            "master_validation": "trabajo/master_validacion.json",
            "generation_log": "trabajo/historial_generacion",
            "pipeline_state": "trabajo/pipeline_estado.json",
        }
    )
    save_project(project)

    summary = {
        "title": master.title,
        "answers": len(master.answers),
        "model": model,
        "generated_at": generated_at,
        "path": str(master_path),
        "validation_path": str(validation_path),
        "generation_log_path": str(generation_log.log_dir),
        "validation_warnings": len(
            [
                issue
                for issue in report.issues
                if issue.level == "warning"
            ]
        ),
        "warnings": master.warnings,
    }
    _emit(progress_callback, 100, "MASTER generado, validado y registrado.")
    return summary


def regenerate_answer(
    project: Project,
    answer_number: int,
) -> dict:
    root = Path(project.root)
    work_dir = root / "trabajo"
    article = _load_json(work_dir / "articulo.json")
    master = _load_json(work_dir / "master.json")

    sections = article.get("sections", [])
    section_index = next(
        (
            index
            for index, item in enumerate(sections)
            if int(item.get("number", 0)) == answer_number
        ),
        None,
    )
    if section_index is None:
        raise MasterGenerationError(
            f"No existe la pregunta número {answer_number}."
        )

    bible_path = work_dir / "citas_extraidas.txt"
    bible_text = (
        bible_path.read_text(encoding="utf-8")
        if bible_path.is_file()
        else ""
    )
    settings = load_settings()
    model = settings.get("openai_model", "gpt-5-mini")
    methodology = load_methodology()
    instructions = _methodology_instructions(methodology)
    editor = OpenAIEditor(model=model)

    current = next(
        (
            item for item in master.get("answers", [])
            if int(item.get("number", 0)) == answer_number
        ),
        {},
    )
    replacement = _generate_one(
        editor=editor,
        instructions=instructions,
        article=article,
        context_builder=ContextBuilder(article, bible_text),
        section_index=section_index,
        model=model,
        log=GenerationLog(root),
        operation="regenerate",
        state_store=PipelineStateStore(root),
        existing_answer=current,
    ).to_dict()

    answers = master.get("answers", [])
    replaced = False
    for index, answer in enumerate(answers):
        if int(answer.get("number", 0)) == answer_number:
            answers[index] = replacement
            replaced = True
            break

    if not replaced:
        answers.append(replacement)
        answers.sort(key=lambda item: int(item.get("number", 0)))

    master["answers"] = answers
    master["generated_at"] = datetime.now().astimezone().isoformat(
        timespec="seconds"
    )

    report = validate_master(article, master)
    (work_dir / "master_validacion.json").write_text(
        json.dumps(report.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    if not report.valid:
        raise MasterGenerationError(
            "La respuesta regenerada no superó la validación."
        )

    (work_dir / "master.json").write_text(
        json.dumps(master, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return replacement


def regenerate_stage(
    project: Project,
    answer_number: int,
    stage_key: str,
) -> dict:
    if stage_key not in {stage.key for stage in PIPELINE_STAGES}:
        raise MasterGenerationError(f"Etapa desconocida: {stage_key}")

    root = Path(project.root)
    work_dir = root / "trabajo"
    article = _load_json(work_dir / "articulo.json")
    master = _load_json(work_dir / "master.json")
    sections = article.get("sections", [])
    section_index = next(
        (
            index for index, item in enumerate(sections)
            if int(item.get("number", 0)) == answer_number
        ),
        None,
    )
    if section_index is None:
        raise MasterGenerationError(
            f"No existe la pregunta número {answer_number}."
        )

    current = next(
        (
            item for item in master.get("answers", [])
            if int(item.get("number", 0)) == answer_number
        ),
        None,
    )
    if current is None:
        raise MasterGenerationError(
            f"El MASTER no contiene la pregunta número {answer_number}."
        )

    bible_path = work_dir / "citas_extraidas.txt"
    bible_text = bible_path.read_text(encoding="utf-8") if bible_path.is_file() else ""
    settings = load_settings()
    model = settings.get("openai_model", "gpt-5-mini")
    methodology = load_methodology()

    replacement = _generate_one(
        editor=OpenAIEditor(model=model),
        instructions=_methodology_instructions(methodology),
        article=article,
        context_builder=ContextBuilder(article, bible_text),
        section_index=section_index,
        model=model,
        log=GenerationLog(root),
        operation="regenerate_stage",
        state_store=PipelineStateStore(root),
        only_stage=stage_key,
        existing_answer=current,
    ).to_dict()
    replacement["status"] = "regenerated"

    for index, item in enumerate(master.get("answers", [])):
        if int(item.get("number", 0)) == answer_number:
            master["answers"][index] = replacement
            break
    master["generated_at"] = datetime.now().astimezone().isoformat(
        timespec="seconds"
    )

    report = validate_master(article, master)
    (work_dir / "master_validacion.json").write_text(
        json.dumps(report.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    if not report.valid:
        raise MasterGenerationError(
            "La etapa regenerada no superó la validación del MASTER."
        )
    (work_dir / "master.json").write_text(
        json.dumps(master, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return replacement
