import unittest
from unittest.mock import patch

import httpx

from ai_agent.config import settings
from ai_agent.provider import GeminiProvider, LocalOpenAIProvider, ProviderError


class FakeResponse:
    def __init__(self, status_code: int, payload: dict) -> None:
        self.status_code = status_code
        self._payload = payload
        self.headers = {}

    def json(self) -> dict:
        return self._payload


class FakeClient:
    responses = []
    last_request = None

    def __init__(self, *args, **kwargs) -> None:
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def post(self, *args, **kwargs):
        self.__class__.last_request = {"args": args, "kwargs": kwargs}
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

    @patch("ai_agent.provider.httpx.Client", FakeClient)
    def test_normalizes_vietnamese_true_false_answer(self) -> None:
        FakeClient.responses = [
            FakeResponse(
                200,
                {
                    "candidates": [
                        {
                            "content": {
                                "parts": [
                                    {
                                        "text": '{"questions":[{"type":"true_false","correct_answer":"Đúng"}]}'
                                    }
                                ]
                            }
                        }
                    ]
                },
            )
        ]

        result = GeminiProvider(sleep=lambda _: None).generate(
            "prompt",
            lambda *values: None,
        )

        self.assertIs(result.payload["questions"][0]["correct_answer"], True)


class LocalOpenAIProviderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original = {
            "LOCAL_INFERENCE_URL": settings.LOCAL_INFERENCE_URL,
            "LOCAL_INFERENCE_SECRET": settings.LOCAL_INFERENCE_SECRET,
            "PROVIDER_RETRY_COUNT": settings.PROVIDER_RETRY_COUNT,
        }
        settings.LOCAL_INFERENCE_URL = "http://local-model/v1/chat/completions"
        settings.LOCAL_INFERENCE_SECRET = "local-secret"
        settings.PROVIDER_RETRY_COUNT = 1

    def tearDown(self) -> None:
        for key, value in self.original.items():
            setattr(settings, key, value)

    @patch("ai_agent.provider.httpx.Client", FakeClient)
    def test_sends_openai_compatible_request_with_authentication(self) -> None:
        FakeClient.responses = [
            FakeResponse(
                200,
                {
                    "choices": [
                        {"message": {"content": '{"questions": []}'}}
                    ]
                },
            )
        ]

        result = LocalOpenAIProvider(
            "quizzvn-question-model:1.0.0",
            sleep=lambda _: None,
        ).generate("prompt", lambda *_: None)

        request = FakeClient.last_request["kwargs"]
        self.assertEqual(result.payload, {"questions": []})
        self.assertEqual(
            request["headers"]["Authorization"],
            "Bearer local-secret",
        )
        self.assertEqual(
            request["json"]["model"],
            "quizzvn-question-model:1.0.0",
        )
        self.assertEqual(request["json"]["response_format"], {"type": "json_object"})

    @patch("ai_agent.provider.httpx.Client", FakeClient)
    def test_retries_retryable_local_model_error(self) -> None:
        FakeClient.responses = [
            FakeResponse(503, {"detail": "model loading"}),
            FakeResponse(
                200,
                {
                    "choices": [
                        {"message": {"content": '{"questions": []}'}}
                    ]
                },
            ),
        ]
        attempts = []

        result = LocalOpenAIProvider(
            "quizzvn-question-model:1.0.0",
            sleep=lambda _: None,
        ).generate("prompt", lambda *values: attempts.append(values))

        self.assertEqual(result.payload, {"questions": []})
        self.assertEqual([item[1] for item in attempts], ["failed", "succeeded"])


if __name__ == "__main__":
    unittest.main()
