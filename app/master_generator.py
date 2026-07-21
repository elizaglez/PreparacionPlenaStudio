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
from app.models.master import MasterAnswer, MasterDocument
from app.prompts import PromptLoader
from app.storage import load_methodology, load_settings
from app.validation.master_validator import validate_master


class MasterGenerationError(RuntimeError):
    pass


ProgressCallback = Callable[[int, str], None]


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
) -> MasterAnswer:
    section = article["sections"][section_index]
    context = context_builder.build(section_index)
    input_text = _build_input(context)

    started = time.perf_counter()
    result = editor.generate_json(
        instructions=instructions,
        input_text=input_text,
    )
    duration = time.perf_counter() - started

    answer = _answer_from_result(section, result)

    log.record(
        question_number=answer.number,
        question=answer.question,
        model=model,
        instructions=instructions,
        input_text=input_text,
        output=result,
        duration_seconds=duration,
        operation=operation,
        warnings=[],
    )
    return answer


def generate_master(
    project: dict,
    progress_callback: ProgressCallback | None = None,
) -> dict:
    root = Path(project.get("root", ""))
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

    project["status"] = "master_validado"
    project["updated_at"] = generated_at
    project.setdefault("outputs", {})
    project["outputs"].update(
        {
            "master": "trabajo/master.json",
            "master_validation": "trabajo/master_validacion.json",
            "generation_log": "trabajo/historial_generacion",
        }
    )
    (root / "proyecto.json").write_text(
        json.dumps(project, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

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
    project: dict,
    answer_number: int,
) -> dict:
    root = Path(project.get("root", ""))
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

    replacement = _generate_one(
        editor=editor,
        instructions=instructions,
        article=article,
        context_builder=ContextBuilder(article, bible_text),
        section_index=section_index,
        model=model,
        log=GenerationLog(root),
        operation="regenerate",
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
