from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from app.ai import OpenAIEditor
from app.context import ContextBuilder
from app.logging import GenerationLog
from app.models import Project
from app.pipeline import PipelineStateStore
from app.storage import load_methodology, load_settings
from app.validation.master_validator import validate_master


class RegenerateStageUseCase:
    def __init__(
        self,
        *,
        pipeline_stages,
        load_json,
        methodology_instructions,
        generate_one,
        error_type,
        settings_loader=load_settings,
        methodology_loader=load_methodology,
        editor_factory=OpenAIEditor,
        context_builder_factory=ContextBuilder,
        generation_log_factory=GenerationLog,
        pipeline_state_factory=PipelineStateStore,
        validator=validate_master,
        now=datetime.now,
    ):
        self.pipeline_stages = pipeline_stages
        self.load_json = load_json
        self.methodology_instructions = methodology_instructions
        self.generate_one = generate_one
        self.error_type = error_type
        self.settings_loader = settings_loader
        self.methodology_loader = methodology_loader
        self.editor_factory = editor_factory
        self.context_builder_factory = context_builder_factory
        self.generation_log_factory = generation_log_factory
        self.pipeline_state_factory = pipeline_state_factory
        self.validator = validator
        self.now = now

    def execute(
        self,
        project: Project,
        answer_number: int,
        stage_key: str,
    ) -> dict:
        if stage_key not in {
            stage.key for stage in self.pipeline_stages
        }:
            raise self.error_type(f"Etapa desconocida: {stage_key}")

        root = Path(project.root)
        work_dir = root / "trabajo"
        article = self.load_json(work_dir / "articulo.json")
        master = self.load_json(work_dir / "master.json")
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
            raise self.error_type(
                f"No existe la pregunta número {answer_number}."
            )

        current = next(
            (
                item
                for item in master.get("answers", [])
                if int(item.get("number", 0)) == answer_number
            ),
            None,
        )
        if current is None:
            raise self.error_type(
                f"El MASTER no contiene la pregunta número {answer_number}."
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

        replacement = self.generate_one(
            project=project,
            editor=self.editor_factory(model=model),
            instructions=self.methodology_instructions(methodology),
            article=article,
            context_builder=self.context_builder_factory(article, bible_text),
            section_index=section_index,
            model=model,
            log=self.generation_log_factory(root),
            operation="regenerate_stage",
            state_store=self.pipeline_state_factory(root),
            only_stage=stage_key,
            existing_answer=current,
        ).to_dict()
        replacement["status"] = "regenerated"

        for index, item in enumerate(master.get("answers", [])):
            if int(item.get("number", 0)) == answer_number:
                master["answers"][index] = replacement
                break
        master["generated_at"] = self.now().astimezone().isoformat(
            timespec="seconds"
        )

        report = self.validator(article, master)
        (work_dir / "master_validacion.json").write_text(
            json.dumps(report.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        if not report.valid:
            raise self.error_type(
                "La etapa regenerada no superó la validación del MASTER."
            )
        (work_dir / "master.json").write_text(
            json.dumps(master, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return replacement
