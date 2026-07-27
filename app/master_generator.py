from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Callable

from app.ai.config import AIProviderConfig
from app.composition import create_article_content_service
from app.config import ROOT_DIR
from app.generation.article_generation_plan import ArticleGenerationPlan
from app.generation.generated_article import GeneratedArticle
from app.models import Project


ProgressCallback = Callable[[int, str], None]


def _emit(callback: ProgressCallback | None, value: int, message: str) -> None:
    if callback:
        callback(value, message)


def _load_json(path: Path) -> dict:
    from app.generation.master_answer_generator import MasterGenerationError

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


def _prompt_loader():
    from app.prompts import PromptLoader

    return PromptLoader(ROOT_DIR / "prompts")


def _methodology_instructions(methodology: dict) -> str:
    principles = "\n".join(
        f"- {item}" for item in methodology.get("principles", [])
    )
    return _prompt_loader().render("system", {"principles": principles})


def _answer_from_result(section: dict, result: dict):
    from app.generation.master_answer_generator import (
        _answer_from_result as legacy_answer_from_result,
    )

    return legacy_answer_from_result(section, result)


def generate_master(
    project: Project,
    progress_callback: ProgressCallback | None = None,
) -> dict:
    from app.ai import OpenAIEditor
    from app.context import ContextBuilder
    from app.generation.master_answer_generator import (
        MasterGenerationError,
        _generate_one,
    )
    from app.logging import GenerationLog
    from app.pipeline import PipelineStateStore
    from app.persistence import save_project
    from app.storage import load_methodology, load_settings
    from app.use_cases.generate_master import GenerateMasterUseCase
    from app.validation.master_validator import validate_master

    use_case = GenerateMasterUseCase(
        load_json=_load_json,
        methodology_instructions=_methodology_instructions,
        generate_one=_generate_one,
        emit=_emit,
        error_type=MasterGenerationError,
        settings_loader=load_settings,
        methodology_loader=load_methodology,
        editor_factory=OpenAIEditor,
        context_builder_factory=ContextBuilder,
        generation_log_factory=GenerationLog,
        pipeline_state_factory=PipelineStateStore,
        validator=validate_master,
        project_saver=save_project,
        now=datetime.now,
    )
    return use_case.execute(project, progress_callback)


def generate_article_content(
    plan: ArticleGenerationPlan,
    provider_name: str,
    config: AIProviderConfig,
) -> GeneratedArticle:
    """Generate article content through the new provider architecture."""
    from app.use_cases.generate_article_content import GenerateArticleContentUseCase

    service = create_article_content_service(provider_name, config)
    return GenerateArticleContentUseCase(service).execute(plan)


def regenerate_answer(
    project: Project,
    answer_number: int,
) -> dict:
    from app.ai import OpenAIEditor
    from app.context import ContextBuilder
    from app.generation.master_answer_generator import (
        MasterGenerationError,
        _generate_one,
    )
    from app.logging import GenerationLog
    from app.pipeline import PipelineStateStore
    from app.storage import load_methodology, load_settings
    from app.use_cases.regenerate_answer import RegenerateAnswerUseCase
    from app.validation.master_validator import validate_master

    use_case = RegenerateAnswerUseCase(
        load_json=_load_json,
        methodology_instructions=_methodology_instructions,
        generate_one=_generate_one,
        error_type=MasterGenerationError,
        settings_loader=load_settings,
        methodology_loader=load_methodology,
        editor_factory=OpenAIEditor,
        context_builder_factory=ContextBuilder,
        generation_log_factory=GenerationLog,
        pipeline_state_factory=PipelineStateStore,
        validator=validate_master,
        now=datetime.now,
    )
    return use_case.execute(project, answer_number)


def regenerate_stage(
    project: Project,
    answer_number: int,
    stage_key: str,
) -> dict:
    from app.ai import OpenAIEditor
    from app.context import ContextBuilder
    from app.generation.master_answer_generator import (
        MasterGenerationError,
        PIPELINE_STAGES,
        _generate_one,
    )
    from app.logging import GenerationLog
    from app.pipeline import PipelineStateStore
    from app.storage import load_methodology, load_settings
    from app.use_cases.regenerate_stage import RegenerateStageUseCase
    from app.validation.master_validator import validate_master

    use_case = RegenerateStageUseCase(
        pipeline_stages=PIPELINE_STAGES,
        load_json=_load_json,
        methodology_instructions=_methodology_instructions,
        generate_one=_generate_one,
        error_type=MasterGenerationError,
        settings_loader=load_settings,
        methodology_loader=load_methodology,
        editor_factory=OpenAIEditor,
        context_builder_factory=ContextBuilder,
        generation_log_factory=GenerationLog,
        pipeline_state_factory=PipelineStateStore,
        validator=validate_master,
        now=datetime.now,
    )
    return use_case.execute(project, answer_number, stage_key)
