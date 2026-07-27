import unittest
from types import SimpleNamespace

import httpx
from openai import (
    APIConnectionError,
    APIResponseValidationError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    InternalServerError,
    PermissionDeniedError,
    RateLimitError,
)

from app.ai.errors import (
    AIProviderConfigurationError,
    AIProviderResponseError,
    AIProviderTemporaryError,
)
from app.ai.openai_client_adapter import OpenAIClientAdapter
from app.ai.openai_client_port import OpenAIClientPort


class SimulatedResponses:
    def __init__(self, *, output_text="Respuesta del SDK", error=None):
        self.output_text = output_text
        self.error = error
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return SimpleNamespace(output_text=self.output_text)


class SimulatedSDKClient:
    def __init__(self, responses):
        self.responses = responses


def _request():
    return httpx.Request("POST", "https://api.openai.com/v1/responses")


def _response(status_code):
    return httpx.Response(status_code, request=_request())


class OpenAIClientAdapterTests(unittest.TestCase):
    def test_implements_port_and_calls_responses_api(self):
        responses = SimulatedResponses(output_text="  Texto generado  ")
        adapter = OpenAIClientAdapter(SimulatedSDKClient(responses))

        result = adapter.generate_text(
            model="modelo-prueba",
            input_text="Contenido para generar",
            temperature=0.4,
            max_output_tokens=800,
            timeout_seconds=25.0,
        )

        self.assertIsInstance(adapter, OpenAIClientPort)
        self.assertEqual(result, "Texto generado")
        self.assertEqual(
            responses.calls,
            [
                {
                    "model": "modelo-prueba",
                    "input": "Contenido para generar",
                    "temperature": 0.4,
                    "max_output_tokens": 800,
                    "timeout": 25.0,
                }
            ],
        )

    def test_rejects_empty_or_invalid_output(self):
        for output_text in (None, "", "   ", 42):
            with self.subTest(output_text=output_text):
                adapter = OpenAIClientAdapter(
                    SimulatedSDKClient(
                        SimulatedResponses(output_text=output_text)
                    )
                )

                with self.assertRaises(AIProviderResponseError):
                    adapter.generate_text(
                        model="modelo-prueba",
                        input_text="Contenido",
                        temperature=None,
                        max_output_tokens=None,
                        timeout_seconds=1.0,
                    )

    def test_translates_timeout_connection_and_rate_limit_errors(self):
        errors = (
            APITimeoutError(_request()),
            APIConnectionError(request=_request()),
            RateLimitError(
                "Límite",
                response=_response(429),
                body=None,
            ),
        )
        for error in errors:
            with self.subTest(error=type(error).__name__):
                adapter = OpenAIClientAdapter(
                    SimulatedSDKClient(SimulatedResponses(error=error))
                )

                with self.assertRaises(AIProviderTemporaryError) as raised:
                    adapter.generate_text(
                        model="modelo-prueba",
                        input_text="Contenido",
                        temperature=None,
                        max_output_tokens=None,
                        timeout_seconds=1.0,
                    )

                self.assertIs(raised.exception.__cause__, error)

    def test_translates_authentication_error(self):
        error = AuthenticationError(
            "Credencial inválida",
            response=_response(401),
            body=None,
        )
        adapter = OpenAIClientAdapter(
            SimulatedSDKClient(SimulatedResponses(error=error))
        )

        with self.assertRaises(AIProviderConfigurationError) as raised:
            adapter.generate_text(
                model="modelo-prueba",
                input_text="Contenido",
                temperature=None,
                max_output_tokens=None,
                timeout_seconds=1.0,
            )

        self.assertIs(raised.exception.__cause__, error)

    def test_translates_permission_and_bad_request_errors(self):
        errors = (
            PermissionDeniedError(
                "Permiso denegado",
                response=_response(403),
                body=None,
            ),
            BadRequestError(
                "Solicitud inválida",
                response=_response(400),
                body=None,
            ),
        )
        for error in errors:
            with self.subTest(error=type(error).__name__):
                adapter = OpenAIClientAdapter(
                    SimulatedSDKClient(SimulatedResponses(error=error))
                )

                with self.assertRaises(
                    AIProviderConfigurationError
                ) as raised:
                    adapter.generate_text(
                        model="modelo-prueba",
                        input_text="Contenido",
                        temperature=None,
                        max_output_tokens=None,
                        timeout_seconds=1.0,
                    )

                self.assertIs(raised.exception.__cause__, error)

    def test_translates_internal_and_generic_server_errors(self):
        errors = (
            InternalServerError(
                "Error interno",
                response=_response(500),
                body=None,
            ),
            APIStatusError(
                "Servicio no disponible",
                response=_response(503),
                body=None,
            ),
        )
        for error in errors:
            with self.subTest(error=type(error).__name__):
                adapter = OpenAIClientAdapter(
                    SimulatedSDKClient(SimulatedResponses(error=error))
                )

                with self.assertRaises(AIProviderTemporaryError) as raised:
                    adapter.generate_text(
                        model="modelo-prueba",
                        input_text="Contenido",
                        temperature=None,
                        max_output_tokens=None,
                        timeout_seconds=1.0,
                    )

                self.assertIs(raised.exception.__cause__, error)

    def test_translates_invalid_and_nonrecoverable_responses(self):
        errors = (
            APIResponseValidationError(
                response=_response(200),
                body={"invalid": True},
            ),
            APIStatusError(
                "No encontrado",
                response=_response(404),
                body=None,
            ),
        )
        for error in errors:
            with self.subTest(error=type(error).__name__):
                adapter = OpenAIClientAdapter(
                    SimulatedSDKClient(SimulatedResponses(error=error))
                )

                with self.assertRaises(AIProviderResponseError) as raised:
                    adapter.generate_text(
                        model="modelo-prueba",
                        input_text="Contenido",
                        temperature=None,
                        max_output_tokens=None,
                        timeout_seconds=1.0,
                    )

                self.assertIs(raised.exception.__cause__, error)


if __name__ == "__main__":
    unittest.main()
