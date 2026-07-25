from __future__ import annotations

from dataclasses import dataclass, field

from app.models import Project
from app.pipeline.stage import PipelineStageResult


@dataclass
class PipelineExecution:
    project: Project
    values: dict[str, str] = field(default_factory=dict)
    results: dict[str, PipelineStageResult] = field(default_factory=dict)
