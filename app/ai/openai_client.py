from __future__ import annotations

import json
import os
from typing import Any

from dotenv import load_dotenv


class AIConfigurationError(RuntimeError):
    pass


class AIResponseError(RuntimeError):
    pass


class OpenAIEditor:
    def __init__(self, model: str = "gpt-5-mini"):
        load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise AIConfigurationError(
                "Falta OPENAI_API_KEY. Escríbela en Configuración y guárdala."
            )

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise AIConfigurationError(
                "No está instalado el paquete openai. Ejecuta: "
                "pip install -r requirements.txt"
            ) from exc

        self.model = model.strip() or "gpt-5-mini"
        self.client = OpenAI(api_key=api_key)

    def generate_json(
        self,
        *,
        instructions: str,
        input_text: str,
    ) -> dict[str, Any]:
        try:
            response = self.client.responses.create(
                model=self.model,
                instructions=instructions,
                input=input_text,
                text={"format": {"type": "json_object"}},
            )
        except Exception as exc:
            raise AIResponseError(f"OpenAI no pudo generar la respuesta: {exc}") from exc

        raw = (response.output_text or "").strip()
        if not raw:
            raise AIResponseError("OpenAI devolvió una respuesta vacía.")

        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise AIResponseError(
                "OpenAI no devolvió JSON válido. No se guardó una respuesta incompleta."
            ) from exc

        if not isinstance(value, dict):
            raise AIResponseError("La respuesta de OpenAI no tiene el formato esperado.")
        return value
