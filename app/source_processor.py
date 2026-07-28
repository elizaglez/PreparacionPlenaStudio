from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Callable
from uuid import uuid4

from app.models import Project
from app.parsers import parse_article
from app.persistence import save_project
from app.readers import inspect_audio, read_bible_source, read_pdf


class SourceProcessingError(RuntimeError):
    pass


ProgressCallback = Callable[[int, str], None]


def _emit(callback: ProgressCallback | None, value: int, message: str) -> None:
    if callback:
        callback(value, message)


def process_project_sources(
    project: Project,
    progress_callback: ProgressCallback | None = None,
) -> dict:
    root = Path(project.root)
    if not root.is_dir():
        raise SourceProcessingError("La carpeta del proyecto no existe.")

    pdf_path = root / project.sources.pdf
    audio_path = root / project.sources.audio
    bible_path = root / project.sources.bible
    work_dir = root / "trabajo"
    work_dir.mkdir(parents=True, exist_ok=True)

    _emit(progress_callback, 8, "Leyendo el PDF…")
    pdf_result = read_pdf(pdf_path)

    _emit(progress_callback, 42, "Estructurando el artículo…")
    article = parse_article(pdf_result)
    article_data = article.to_dict()

    _emit(progress_callback, 60, "Leyendo las citas bíblicas…")
    bible_result = read_bible_source(bible_path)

    _emit(progress_callback, 73, "Validando el audio…")
    audio_result = inspect_audio(audio_path)

    analysis_output_paths = (
        work_dir / "pdf_extraido.txt",
        work_dir / "citas_extraidas.txt",
        work_dir / "articulo.json",
        work_dir / "fuentes_resumen.json",
    )
    previous_analysis_outputs = {
        path: path.read_bytes() if path.is_file() else None
        for path in analysis_output_paths
    }

    _emit(progress_callback, 84, "Guardando los textos y la estructura…")
    (work_dir / "pdf_extraido.txt").write_text(
        pdf_result["text"], encoding="utf-8"
    )
    (work_dir / "citas_extraidas.txt").write_text(
        bible_result["text"], encoding="utf-8"
    )
    (work_dir / "articulo.json").write_text(
        json.dumps(article_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    summary = {
        "processed_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "project": project.name,
        "pdf": {
            key: value
            for key, value in pdf_result.items()
            if key not in {"text", "pages"}
        },
        "article": {
            "title": article.title,
            "sections": len(article.sections),
            "headings": len(article.detected_headings),
            "unassigned_paragraphs": len(article.unassigned_paragraphs),
            "warnings": article.parser_warnings,
        },
        "bible": {
            key: value for key, value in bible_result.items() if key != "text"
        },
        "audio": audio_result,
        "diagnostics": {
            "pdf_pages": pdf_result["page_count"],
            "pdf_characters": pdf_result["character_count"],
            "detected_questions": len(pdf_result["questions"]),
            "structured_sections": len(article.sections),
            "detected_scripture_references": len(
                pdf_result["scripture_references"]
            ),
            "bible_characters": bible_result["character_count"],
            "audio_transcription": audio_result["transcription_status"],
            "parser_warnings": len(article.parser_warnings),
        },
    }

    _emit(progress_callback, 94, "Guardando el diagnóstico…")
    (work_dir / "fuentes_resumen.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    generated_article_path = work_dir / "articulo_generado.json"
    legacy_output_paths = (
        work_dir / "master.json",
        work_dir / "master_validacion.json",
        work_dir / "pipeline_estado.json",
    )
    stale_output_keys = (
        "generated_article",
        "master",
        "master_validation",
        "pipeline_state",
    )

    previous_status = project.status
    previous_updated_at = project.updated_at
    previous_outputs = dict(project.outputs)
    project.status = "articulo_estructurado"
    project.updated_at = summary["processed_at"]
    project.outputs.update(
        {
            "pdf_text": "trabajo/pdf_extraido.txt",
            "bible_text": "trabajo/citas_extraidas.txt",
            "article": "trabajo/articulo.json",
            "sources_summary": "trabajo/fuentes_resumen.json",
        }
    )
    for key in stale_output_keys:
        project.outputs.pop(key, None)

    try:
        save_project(project)
    except Exception:
        project.status = previous_status
        project.updated_at = previous_updated_at
        project.outputs.clear()
        project.outputs.update(previous_outputs)
        for path, previous_content in previous_analysis_outputs.items():
            if previous_content is None:
                path.unlink(missing_ok=True)
            else:
                path.write_bytes(previous_content)
        raise

    existing_legacy_outputs = [
        path
        for path in legacy_output_paths
        if path.is_file()
    ]
    if existing_legacy_outputs:
        archive_dir = (
            work_dir
            / "archivados"
            / f"master_{uuid4().hex}"
        )
        archive_dir.mkdir(parents=True)
        for path in existing_legacy_outputs:
            path.replace(archive_dir / path.name)

    generated_article_path.unlink(missing_ok=True)

    _emit(progress_callback, 100, "Artículo estructurado correctamente.")
    return summary
