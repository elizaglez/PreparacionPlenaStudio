from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Callable

from app.readers import inspect_audio, read_bible_source, read_pdf


class SourceProcessingError(RuntimeError):
    pass


ProgressCallback = Callable[[int, str], None]


def _emit(callback: ProgressCallback | None, value: int, message: str) -> None:
    if callback:
        callback(value, message)


def process_project_sources(
    project: dict,
    progress_callback: ProgressCallback | None = None,
) -> dict:
    root = Path(project.get("root", ""))
    if not root.is_dir():
        raise SourceProcessingError("La carpeta del proyecto no existe.")

    sources = project.get("sources", {})
    pdf_path = root / sources.get("pdf", "")
    audio_path = root / sources.get("audio", "")
    bible_path = root / sources.get("bible", "")
    work_dir = root / "trabajo"
    work_dir.mkdir(parents=True, exist_ok=True)

    _emit(progress_callback, 10, "Leyendo el PDF…")
    pdf_result = read_pdf(pdf_path)

    _emit(progress_callback, 50, "Leyendo las citas bíblicas…")
    bible_result = read_bible_source(bible_path)

    _emit(progress_callback, 70, "Validando el audio…")
    audio_result = inspect_audio(audio_path)

    _emit(progress_callback, 82, "Guardando los textos extraídos…")
    (work_dir / "pdf_extraido.txt").write_text(
        pdf_result["text"], encoding="utf-8"
    )
    (work_dir / "citas_extraidas.txt").write_text(
        bible_result["text"], encoding="utf-8"
    )

    summary = {
        "processed_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "project": project.get("name", ""),
        "pdf": {
            key: value
            for key, value in pdf_result.items()
            if key not in {"text", "pages"}
        },
        "bible": {
            key: value for key, value in bible_result.items() if key != "text"
        },
        "audio": audio_result,
        "diagnostics": {
            "pdf_pages": pdf_result["page_count"],
            "pdf_characters": pdf_result["character_count"],
            "detected_questions": len(pdf_result["questions"]),
            "detected_scripture_references": len(
                pdf_result["scripture_references"]
            ),
            "bible_characters": bible_result["character_count"],
            "audio_transcription": audio_result["transcription_status"],
        },
    }

    _emit(progress_callback, 92, "Guardando el diagnóstico…")
    summary_path = work_dir / "fuentes_resumen.json"
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    project["status"] = "fuentes_procesadas"
    project["updated_at"] = summary["processed_at"]
    project.setdefault("outputs", {})
    project["outputs"].update(
        {
            "pdf_text": "trabajo/pdf_extraido.txt",
            "bible_text": "trabajo/citas_extraidas.txt",
            "sources_summary": "trabajo/fuentes_resumen.json",
        }
    )
    (root / "proyecto.json").write_text(
        json.dumps(project, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    _emit(progress_callback, 100, "Fuentes procesadas correctamente.")
    return summary
