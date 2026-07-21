from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class StageStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class PipelineStage:
    key: str
    label: str
    output_field: str
    required: bool = False
    dependencies: tuple[str, ...] = ()


@dataclass
class PipelineStageResult:
    key: str
    status: StageStatus = StageStatus.PENDING
    value: str = ""
    source_notes: list[str] = field(default_factory=list)
    error: str = ""
    started_at: str = ""
    completed_at: str = ""
    duration_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        return data
