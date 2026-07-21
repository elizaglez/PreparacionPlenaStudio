from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any


class PipelineStateStore:
    """Persists resumable per-question pipeline state in trabajo/pipeline_estado.json."""

    def __init__(self, project_root: str | Path):
        self.path = Path(project_root) / "trabajo" / "pipeline_estado.json"

    def load(self) -> dict[str, Any]:
        if not self.path.is_file():
            return {"version": 1, "questions": {}}
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {"version": 1, "questions": {}}
        if not isinstance(value, dict):
            return {"version": 1, "questions": {}}
        value.setdefault("version", 1)
        value.setdefault("questions", {})
        return value

    def save(self, state: dict[str, Any]) -> None:
        payload = deepcopy(state)
        payload["updated_at"] = datetime.now().astimezone().isoformat(
            timespec="seconds"
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def update_stage(
        self,
        *,
        question_number: int,
        question: str,
        stage_key: str,
        stage_data: dict[str, Any],
    ) -> None:
        state = self.load()
        questions = state.setdefault("questions", {})
        item = questions.setdefault(str(question_number), {})
        item["question"] = question
        item.setdefault("stages", {})[stage_key] = deepcopy(stage_data)
        self.save(state)
