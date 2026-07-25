from __future__ import annotations

import json
from pathlib import Path

from app.models import Project


class WordExportError(RuntimeError):
    pass


def export_master_to_docx(project: Project) -> Path:
    try:
        from docx import Document
        from docx.shared import Pt
    except ImportError as exc:
        raise WordExportError(
            "No está instalado python-docx. Ejecuta pip install -r requirements.txt."
        ) from exc

    root = Path(project.root)
    master_path = root / "trabajo" / "master.json"
    if not master_path.is_file():
        raise WordExportError("Primero genera el MASTER.")

    try:
        master = json.loads(master_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise WordExportError("master.json contiene datos inválidos.") from exc

    output_dir = root / "salidas"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "MASTER.docx"

    document = Document()
    styles = document.styles
    styles["Normal"].font.name = "Aptos"
    styles["Normal"].font.size = Pt(11)

    document.add_heading(master.get("title", "MASTER"), level=0)
    intro = master.get("introduction", "").strip()
    if intro:
        document.add_paragraph(intro)

    for item in master.get("answers", []):
        question = item.get("question", "")
        document.add_heading(question, level=1)
        document.add_paragraph(item.get("answer", ""))

        optional = [
            ("Explicación bíblica", item.get("scripture_explanation", "")),
            ("Comparación", item.get("comparison", "")),
            ("Aplicación", item.get("application", "")),
            ("Nota de imagen", item.get("image_note", "")),
        ]
        for label, value in optional:
            if str(value).strip():
                paragraph = document.add_paragraph()
                paragraph.add_run(f"{label}: ").bold = True
                paragraph.add_run(str(value).strip())

        scriptures = item.get("scriptures", [])
        if scriptures:
            paragraph = document.add_paragraph()
            paragraph.add_run("Textos bíblicos: ").bold = True
            paragraph.add_run(", ".join(scriptures))

    conclusion = master.get("conclusion", "").strip()
    if conclusion:
        document.add_heading("Conclusión", level=1)
        document.add_paragraph(conclusion)

    document.save(output_path)
    return output_path
