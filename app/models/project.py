from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProjectSources:
    pdf: str = ""
    audio: str = ""
    bible: str = ""

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)


@dataclass
class Project:
    name: str
    version: str = "0.1.0"
    status: str = "nuevo"
    created_at: str = ""
    updated_at: str = ""
    root: str = ""
    sources: ProjectSources = field(default_factory=ProjectSources)
    outputs: dict[str, str] = field(default_factory=dict)
    pipeline_values: dict[str, str] = field(default_factory=dict, repr=False)
    pipeline_results: dict[str, Any] = field(default_factory=dict, repr=False)

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)
