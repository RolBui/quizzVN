import math
from typing import Any
from urllib.parse import quote

import httpx

from ai_agent.config import settings


class EmbeddingError(RuntimeError):
    pass


def embed_documents(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    requests = [
        {
            "model": f"models/{settings.EMBEDDING_MODEL}",
            "content": {"parts": [{"text": f"title: approved question | text: {text}"}]},
            "outputDimensionality": settings.EMBEDDING_DIMENSIONS,
        }
        for text in texts
    ]
    payload = _post_embedding("batchEmbedContents", {"requests": requests})
    embeddings = payload.get("embeddings")
    if not isinstance(embeddings, list) or len(embeddings) != len(texts):
        raise EmbeddingError("Gemini returned an invalid embedding batch")
    return [_read_values(item) for item in embeddings]


def embed_query(text: str) -> list[float]:
    payload = _post_embedding(
        "embedContent",
        {
            "content": {
                "parts": [
                    {"text": f"task: search result | query: {text}"},
                ]
            },
            "outputDimensionality": settings.EMBEDDING_DIMENSIONS,
        },
    )
    embedding = payload.get("embedding")
    if not isinstance(embedding, dict):
        raise EmbeddingError("Gemini returned an invalid query embedding")
    return _read_values(embedding)


def _post_embedding(method: str, body: dict[str, Any]) -> dict[str, Any]:
    if not settings.GEMINI_API_KEY:
        raise EmbeddingError("GEMINI_API_KEY is required for RAG embeddings")
    model = quote(settings.EMBEDDING_MODEL, safe="-._")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:{method}"
    try:
        with httpx.Client(timeout=settings.EMBEDDING_TIMEOUT_SECONDS) as client:
            response = client.post(
                url,
                headers={"x-goog-api-key": settings.GEMINI_API_KEY},
                json=body,
            )
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise EmbeddingError(f"Gemini embedding request failed: {exc}") from exc
    if not isinstance(payload, dict):
        raise EmbeddingError("Gemini returned a non-object embedding response")
    return payload


def _read_values(payload: dict[str, Any]) -> list[float]:
    values = payload.get("values")
    if not isinstance(values, list) or len(values) != settings.EMBEDDING_DIMENSIONS:
        raise EmbeddingError(
            "Gemini embedding dimension does not match "
            f"AI_AGENT_EMBEDDING_DIMENSIONS={settings.EMBEDDING_DIMENSIONS}"
        )
    result = [float(value) for value in values]
    if not all(math.isfinite(value) for value in result):
        raise EmbeddingError("Gemini returned a non-finite embedding value")
    return result
