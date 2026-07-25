from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Callable

from app.ai import OpenAIEditor
from app.context import ContextBuilder
from app.logging import GenerationLog
from app.models import Project
from app.models.master import MasterAnswer, MasterDocument
from app.pipeline import PipelineStateStore
from app.persistence import save_project
from app.storage import load_methodology, load_settings
from app.validation.master_validator import validate_master


ProgressCallback = Callable[[int, str], None]


class GenerateMasterUseCase:
    def __init__(
        self,
        *,
        load_json,
        methodology_instructions,
        generate_one,
        emit,
        error_type,
        settings_loader=load_settings,
        methodology_loader=load_methodology,
        editor_factory=OpenAIEditor,
        context_builder_factory=ContextBuilder,
        generation_log_factory=GenerationLog,
        pipeline_state_factory=PipelineStateStore,
        validator=validate_master,
        project_saver=save_project,
        now=datetime.now,
    ):
        self.load_json = load_json
        self.methodology_instructions = methodology_instructions
        self.generate_one = generate_one
        self.emit = emit
        self.error_type = error_type
        self.settings_loader = settings_loader
        self.methodology_loader = methodology_loader
        self.editor_factory = editor_factory
        self.context_builder_factory = context_builder_factory
        self.generation_log_factory = generation_log_factory
        self.pipeline_state_factory = pipeline_state_factory
        self.validator = validator
        self.project_saver = project_saver
        self.now = now

    def execute(
        self,
        project: Project,
        progress_callback: ProgressCallback | None = None,
    ) -> dict:
        root = Path(project.root)
        if not root.is_dir():
            raise self.error_type("La carpeta del proyecto no existe.")

        work_dir = root / "trabajo"
        article = self.load_json(work_dir / "articulo.json")
        sections = article.get("sections", [])
        if not isinstance(sections, list) or not sections:
            raise self.error_type(
                "articulo.json no contiene preguntas estructuradas."
            )

        bible_path = work_dir / "citas_extraidas.txt"
        bible_text = (
            bible_path.read_text(encoding="utf-8")
            if bible_path.is_file()
            else ""
        )

        settings = self.settings_loader()
        model = settings.get("openai_model", "gpt-5-mini")
        methodology = self.methodology_loader()
        instructions = self.methodology_instructions(methodology)
        editor = self.editor_factory(model=model)
        context_builder = self.context_builder_factory(article, bible_text)
        generation_log = self.generation_log_factory(root)
        pipeline_state = self.pipeline_state_factory(root)

        answers: list[MasterAnswer] = []
        total = len(sections)

        for index in range(total):
            progress = 5 + int((index / total) * 80)
            self.emit(
                progress_callback,
                progress,
                f"Generando respuesta {index + 1} de {total}…",
            )
            answers.append(
                self.generate_one(
                    project=project,
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

        generated_at = self.now().astimezone().isoformat(
            timespec="seconds"
        )
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

        self.emit(progress_callback, 88, "Validando el MASTER…")
        report = self.validator(article, master_data)
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
            raise self.error_type(
                "El MASTER no superó la validación:\n- "
                + "\n- ".join(errors)
            )

        self.emit(progress_callback, 94, "Guardando master.json…")
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
        self.project_saver(project)

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
        self.emit(
            progress_callback,
            100,
            "MASTER generado, validado y registrado.",
        )
        return summary
