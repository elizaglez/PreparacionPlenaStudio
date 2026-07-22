from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.models import Project, ProjectSources
from app.storage import add_recent_project


def _from_dict(data: dict[str, Any], root: Path) -> Project:
    sources = data.get("sources", {})
    if not isinstance(sources, dict):
        sources = {}
    outputs = data.get("outputs", {})
    if not isinstance(outputs, dict):
        outputs = {}
    return Project(
        name=str(data.get("name", "")),
        version=str(data.get("version", "0.1.0")),
        status=str(data.get("status", "nuevo")),
        created_at=str(data.get("created_at", "")),
        updated_at=str(data.get("updated_at", "")),
        root=str(root.resolve()),
        sources=ProjectSources(
            pdf=str(sources.get("pdf", "")),
            audio=str(sources.get("audio", "")),
            bible=str(sources.get("bible", "")),
        ),
        outputs={str(key): str(value) for key, value in outputs.items()},
    )


def _to_dict(project: Project) -> dict[str, Any]:
    return {
        "name": project.name,
        "version": project.version,
        "status": project.status,
        "created_at": project.created_at,
        "updated_at": project.updated_at,
        "root": project.root,
        "sources": {
            "pdf": project.sources.pdf,
            "audio": project.sources.audio,
            "bible": project.sources.bible,
        },
        "outputs": dict(project.outputs),
    }


def load_project(path: str | Path) -> Project:
    project_path = Path(path)
    if project_path.is_dir():
        project_path = project_path / "proyecto.json"
    data = json.loads(project_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("proyecto.json no contiene un objeto JSON.")
    return _from_dict(data, project_path.parent)


def save_project(project: Project) -> None:
    path = Path(project.root) / "proyecto.json"
    path.write_text(
        json.dumps(_to_dict(project), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def remember_project(project: Project) -> None:
    add_recent_project(_to_dict(project))
