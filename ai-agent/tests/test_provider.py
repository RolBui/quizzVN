import unittest
from unittest.mock import patch

import httpx

from ai_agent.config import settings
from ai_agent.provider import GeminiProvider, ProviderError


class FakeResponse:
    def __init__(self, status_code: int, payload: dict) -> None:
        self.status_code = status_code
        self._payload = payload
        self.headers = {}

    def json(self) -> dict:
        return self._payload


class FakeClient:
    responses = []

    def __init__(self, *args, **kwargs) -> None:
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def post(self, *args, **kwargs):
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return response


class GeminiProviderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_key = settings.GEMINI_API_KEY
        self.original_retries = settings.PROVIDER_RETRY_COUNT
        settings.GEMINI_API_KEY = "test-key"
        settings.PROVIDER_RETRY_COUNT = 2

    def tearDown(self) -> None:
        settings.GEMINI_API_KEY = self.original_key
        settings.PROVIDER_RETRY_COUNT = self.original_retries

    @patch("ai_agent.provider.httpx.Client", FakeClient)
    def test_retries_503_then_succeeds(self) -> None:
        FakeClient.responses = [
            FakeResponse(503, {"error": {"message": "high demand"}}),
            FakeResponse(
                200,
                {
                    "candidates": [
                        {"content": {"parts": [{"text": '{"questions": []}'}]}}
                    ]
                },
            ),
        ]
        attempts = []

        result = GeminiProvider(sleep=lambda _: None).generate(
            "prompt",
            lambda *values: attempts.append(values),
        )

        self.assertEqual(result.payload, {"questions": []})
        self.assertEqual([item[1] for item in attempts], ["failed", "succeeded"])

    @patch("ai_agent.provider.httpx.Client", FakeClient)
    def test_does_not_retry_non_retryable_400(self) -> None:
        FakeClient.responses = [FakeResponse(400, {"error": {"message": "bad request"}})]
        attempts = []

        with self.assertRaises(ProviderError):
            GeminiProvider(sleep=lambda _: None).generate(
                "prompt",
                lambda *values: attempts.append(values),
            )

        self.assertEqual(len(attempts), 1)

    @patch("ai_agent.provider.httpx.Client", FakeClient)
    def test_retries_network_error_then_succeeds(self) -> None:
        FakeClient.responses = [
            httpx.ConnectError("connection reset"),
            FakeResponse(
                200,
                {
                    "candidates": [
                        {"content": {"parts": [{"text": '{"questions": []}'}]}}
                    ]
                },
            ),
        ]
        attempts = []

        result = GeminiProvider(sleep=lambda _: None).generate(
            "prompt",
            lambda *values: attempts.append(values),
        )

        self.assertEqual(result.payload, {"questions": []})
        self.assertEqual([item[1] for item in attempts], ["failed", "succeeded"])


if __name__ == "__main__":
    unittest.main()
