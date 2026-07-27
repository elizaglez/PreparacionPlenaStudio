from __future__ import annotations

import os
from collections.abc import Callable


class SecretNotFoundError(RuntimeError):
    """Raised when a required secret is missing from its external source."""


class SecretLoader:
    """Read secrets on demand without caching or exposing their values."""

    def __init__(
        self,
        source: Callable[[str], str | None] | None = None,
    ) -> None:
        self._source = os.getenv if source is None else source

    def get_secret(self, name: str) -> str:
        if not isinstance(name, str) or not name.strip():
            raise SecretNotFoundError(
                "El nombre del secreto no puede estar vacío."
            )

        normalized_name = name.strip()
        value = self._source(normalized_name)
        if not isinstance(value, str) or not value.strip():
            raise SecretNotFoundError(
                f"Falta el secreto requerido: {normalized_name}."
            )
        return value.strip()
