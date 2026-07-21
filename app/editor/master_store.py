from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any


class MasterStoreError(RuntimeError):
    pass


ALLOWED_STATUSES = {"pending", "reviewed", "approved", "regenerated", "edited"}


class MasterStore:
    def __init__(self, project_root: str | Path):
        self.project_root = Path(project_root)
        self.master_path = self.project_root / "trabajo" / "master.json"

    def load(self) -> dict[str, Any]:
        if not self.master_path.is_file():
            raise MasterStoreError("Primero genera el MASTER.")
        try:
            master = json.loads(self.master_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise MasterStoreError("master.json contiene JSON inválido.") from exc
        if not isinstance(master, dict):
            raise MasterStoreError("master.json no tiene la estructura esperada.")

        changed = False
        for answer in master.get("answers", []):
            if "status" not in answer:
                answer["status"] = "pending"
                changed = True
        if changed:
            self.save(master)
        return master

    def save(self, master: dict[str, Any]) -> None:
        data = deepcopy(master)
        data["updated_at"] = datetime.now().astimezone().isoformat(
            timespec="seconds"
        )
        self.master_path.parent.mkdir(parents=True, exist_ok=True)
        self.master_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def update_answer(
        self,
        number: int,
        fields: dict[str, Any],
        *,
        status: str = "edited",
    ) -> dict[str, Any]:
        if status not in ALLOWED_STATUSES:
            raise MasterStoreError(f"Estado no permitido: {status}")

        master = self.load()
        answer = next(
            (
                item for item in master.get("answers", [])
                if int(item.get("number", 0)) == number
            ),
            None,
        )
        if answer is None:
            raise MasterStoreError(f"No existe la respuesta número {number}.")

        editable = {
            "answer",
            "scripture_explanation",
            "comparison",
            "application",
            "image_note",
        }
        for key, value in fields.items():
            if key in editable:
                answer[key] = str(value).strip()

        answer["status"] = status
        answer["edited_at"] = datetime.now().astimezone().isoformat(
            timespec="seconds"
        )
        self.save(master)
        return deepcopy(answer)

    def set_status(self, number: int, status: str) -> dict[str, Any]:
        return self.update_answer(number, {}, status=status)

    def progress(self) -> dict[str, int]:
        master = self.load()
        answers = master.get("answers", [])
        return {
            "total": len(answers),
            "reviewed": sum(
                1 for item in answers
                if item.get("status") in {"reviewed", "approved"}
            ),
            "approved": sum(
                1 for item in answers if item.get("status") == "approved"
            ),
        }
