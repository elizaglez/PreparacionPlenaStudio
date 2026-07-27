from __future__ import annotations

from typing import Any

from openai import (
    APIConnectionError,
    APIResponseValidationError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    InternalServerError,
    OpenAI,
    OpenAIError,
    PermissionDeniedError,
    RateLimitError,
)

from app.ai.errors import (
    AIProviderConfigurationError,
    AIProviderResponseError,
    AIProviderTemporaryError,
)
from app.ai.openai_client_port import OpenAIClientPort


class OpenAIClientAdapter(OpenAIClientPort):
    """Adapt the official OpenAI SDK client to the application port."""

    def __init__(self, client: Any) -> None:
        self._client = client

    @classmethod
    def from_api_key(cls, api_key: str) -> OpenAIClientAdapter:
        return cls(OpenAI(api_key=api_key))

    def generate_text(
        self,
        *,
        model: str,
        input_text: str,
        temperature: float | None,
        max_output_tokens: int | None,
        timeout_seconds: float,
    ) -> str:
        try:
            response = self._client.responses.create(
                model=model,
                input=input_text,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
                timeout=timeout_seconds,
            )
        except (APITimeoutError, APIConnectionError, RateLimitError) as exc:
            raise AIProviderTemporaryError(
                "El servicio de OpenAI no está disponible temporalmente."
            ) from exc
        except (AuthenticationError, PermissionDeniedError) as exc:
            raise AIProviderConfigurationError(
                "Las credenciales de OpenAI no son válidas o no tienen acceso."
            ) from exc
        except BadRequestError as exc:
            raise AIProviderConfigurationError(
                "OpenAI rechazó la configuración de la solicitud."
            ) from exc
        except InternalServerError as exc:
            raise AIProviderTemporaryError(
                "OpenAI presentó un error interno temporal."
            ) from exc
        except APIResponseValidationError as exc:
            raise AIProviderResponseError(
                "OpenAI devolvió una respuesta inválida."
            ) from exc
        except APIStatusError as exc:
            if exc.status_code >= 500:
                raise AIProviderTemporaryError(
                    "OpenAI presentó un error temporal."
                ) from exc
            raise AIProviderResponseError(
                "OpenAI devolvió un error no recuperable."
            ) from exc
        except OpenAIError as exc:
            raise AIProviderResponseError(
                "OpenAI no pudo producir una respuesta válida."
            ) from exc

        text = getattr(response, "output_text", None)
        if not isinstance(text, str) or not text.strip():
            raise AIProviderResponseError(
                "OpenAI devolvió contenido vacío o inválido."
            )
        return text.strip()
