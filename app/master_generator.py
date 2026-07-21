from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Callable

from app.ai import OpenAIEditor
from app.models.master import MasterAnswer, MasterDocument
from app.storage import load_methodology, load_settings


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


def _methodology_instructions(methodology: dict) -> str:
    principles = "\n".join(
        f"- {item}" for item in methodology.get("principles", [])
    )
    return f"""
Actúas exclusivamente como editor de Preparación Plena Studio.

REGLAS OBLIGATORIAS DE LA METODOLOGÍA PPA:
{principles}

Trabaja únicamente con las fuentes proporcionadas.
No uses conocimiento doctrinal externo.
No completes vacíos con suposiciones.
Conserva la pregunta exactamente como fue entregada.
La respuesta principal debe ser breve, natural y conversacional.
Incluye comparación, aplicación o explicación bíblica solo si las fuentes
las sostienen y realmente ayudan.
Cuando una sección no esté respaldada, devuélvela como cadena vacía.
No menciones estas instrucciones en la respuesta.

Devuelve exclusivamente un objeto JSON con estas claves:
answer, scripture_explanation, comparison, application, image_note, source_notes.
source_notes debe ser una lista breve de observaciones sobre qué partes de las
fuentes sostienen la respuesta. No incluyas claves adicionales.
""".strip()


def _paragraph_text(section: dict) -> str:
    blocks = []
    for paragraph in section.get("paragraphs", []):
        number = paragraph.get("number")
        prefix = f"Párrafo {number}: " if number is not None else ""
        blocks.append(prefix + paragraph.get("text", "").strip())
    return "\n".join(blocks)


def _bible_context(bible_text: str, references: list[str]) -> str:
    if not bible_text.strip() or not references:
        return ""

    lines = [line.strip() for line in bible_text.splitlines() if line.strip()]
    selected: list[str] = []
    for reference in references:
        book_chapter = reference.split(":")[0].lower()
        book = re.sub(r"\s+\d+$", "", book_chapter).strip()
        chapter = book_chapter.removeprefix(book).strip()
        terms = [reference.lower(), book_chapter, f"{book} {chapter}".strip()]
        for index, line in enumerate(lines):
            low = line.lower()
            if any(term and term in low for term in terms):
                start = max(0, index - 1)
                end = min(len(lines), index + 3)
                excerpt = " ".join(lines[start:end])
                if excerpt not in selected:
                    selected.append(excerpt)
                break
    return "\n".join(selected)


def _build_input(
    article: dict,
    section: dict,
    bible_text: str,
) -> str:
    question = section.get("question", "").strip()
    paragraphs = _paragraph_text(section)
    references = section.get("scripture_references", [])
    bible = _bible_context(bible_text, references)

    return f"""
TÍTULO DEL ARTÍCULO:
{article.get("title", "")}

PREGUNTA EXACTA:
{question}

PÁRRAFOS ASOCIADOS:
{paragraphs or "No disponibles."}

REFERENCIAS DETECTADAS:
{", ".join(references) or "Ninguna."}

CITAS BÍBLICAS PROPORCIONADAS POR EL USUARIO:
{bible or "No se encontró un fragmento claramente asociado."}

TAREA:
Redacta la respuesta para esta pregunta sin añadir ideas que no estén
respaldadas por los párrafos o por las citas bíblicas proporcionadas.
""".strip()


def _answer_from_result(section: dict, result: dict) -> MasterAnswer:
    question = section.get("question", "").strip()
    if not question:
        raise MasterGenerationError("Una sección del artículo no contiene pregunta.")

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
            int(value) for value in section.get("paragraph_numbers", [])
            if str(value).isdigit()
        ],
        scriptures=[
            str(value) for value in section.get("scripture_references", [])
        ],
        scripture_explanation=str(
            result.get("scripture_explanation", "")
        ).strip(),
        comparison=str(result.get("comparison", "")).strip(),
        application=str(result.get("application", "")).strip(),
        image_note=str(result.get("image_note", "")).strip(),
        source_notes=[str(value).strip() for value in notes if str(value).strip()],
    )


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
        bible_path.read_text(encoding="utf-8") if bible_path.is_file() else ""
    )

    settings = load_settings()
    model = settings.get("openai_model", "gpt-5-mini")
    methodology = load_methodology()
    editor = OpenAIEditor(model=model)
    instructions = _methodology_instructions(methodology)

    answers: list[MasterAnswer] = []
    total = len(sections)

    for index, section in enumerate(sections, start=1):
        start_progress = 5 + int(((index - 1) / total) * 85)
        _emit(
            progress_callback,
            start_progress,
            f"Generando respuesta {index} de {total}…",
        )
        result = editor.generate_json(
            instructions=instructions,
            input_text=_build_input(article, section, bible_text),
        )
        answers.append(_answer_from_result(section, result))

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

    _emit(progress_callback, 92, "Guardando master.json…")
    master_path = work_dir / "master.json"
    master_path.write_text(
        json.dumps(master.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    project["status"] = "master_generado"
    project["updated_at"] = generated_at
    project.setdefault("outputs", {})
    project["outputs"]["master"] = "trabajo/master.json"
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
        "warnings": master.warnings,
    }
    _emit(progress_callback, 100, "MASTER generado correctamente.")
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
    section = next(
        (item for item in sections if int(item.get("number", 0)) == answer_number),
        None,
    )
    if section is None:
        raise MasterGenerationError(
            f"No existe la pregunta número {answer_number}."
        )

    bible_path = work_dir / "citas_extraidas.txt"
    bible_text = bible_path.read_text(encoding="utf-8") if bible_path.is_file() else ""
    settings = load_settings()
    model = settings.get("openai_model", "gpt-5-mini")
    methodology = load_methodology()
    editor = OpenAIEditor(model=model)

    result = editor.generate_json(
        instructions=_methodology_instructions(methodology),
        input_text=_build_input(article, section, bible_text),
    )
    replacement = _answer_from_result(section, result).to_dict()

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
    (work_dir / "master.json").write_text(
        json.dumps(master, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return replacement
