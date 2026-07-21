from __future__ import annotations

from pathlib import Path
from string import Template
from typing import Any


class PromptNotFoundError(RuntimeError):
    pass


class PromptRenderError(RuntimeError):
    pass


class PromptLoader:
    def __init__(self, prompt_dir: Path):
        self.prompt_dir = Path(prompt_dir)

    def load(self, name: str) -> str:
        path = self.prompt_dir / f"{name}.md"
        if not path.is_file():
            raise PromptNotFoundError(f"No existe el prompt: {path.name}")
        return path.read_text(encoding="utf-8").strip()

    def render(self, name: str, values: dict[str, Any]) -> str:
        template = Template(self.load(name))
        normalized = {
            key: "" if value is None else str(value)
            for key, value in values.items()
        }
        try:
            return template.substitute(normalized)
        except KeyError as exc:
            raise PromptRenderError(
                f"Falta el valor requerido por el prompt {name}: {exc.args[0]}"
            ) from exc
