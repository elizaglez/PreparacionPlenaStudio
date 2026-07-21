from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


class GenerationLog:
    def __init__(self, project_root: str | Path):
        self.root = Path(project_root)
        self.log_dir = self.root / "trabajo" / "historial_generacion"
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def record(
        self,
        *,
        question_number: int,
        question: str,
        model: str,
        instructions: str,
        input_text: str,
        output: dict[str, Any],
        duration_seconds: float,
        operation: str,
        warnings: list[str] | None = None,
    ) -> Path:
        timestamp = datetime.now().astimezone()
        filename = (
            f"{timestamp.strftime('%Y%m%d_%H%M%S_%f')}_"
            f"pregunta_{question_number}_{operation}.json"
        )
        path = self.log_dir / filename
        payload = {
            "timestamp": timestamp.isoformat(timespec="seconds"),
            "operation": operation,
            "question_number": question_number,
            "question": question,
            "model": model,
            "duration_seconds": round(duration_seconds, 3),
            "instructions": instructions,
            "input": input_text,
            "output": output,
            "warnings": warnings or [],
        }
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return path

    def list_entries(self) -> list[Path]:
        return sorted(
            self.log_dir.glob("*.json"),
            key=lambda path: path.name,
            reverse=True,
        )
