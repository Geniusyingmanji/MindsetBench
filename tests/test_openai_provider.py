import asyncio
import io
import json
from urllib.error import HTTPError

import pytest

from mindsetbench.models.prompt import Condition, PromptArtifact
from mindsetbench.models.run import ModelRequest
from mindsetbench.runner.providers import OpenAICompatibleProvider


def _request() -> ModelRequest:
    return ModelRequest(
        model="test-model",
        prompt=PromptArtifact(
            case_id="case-1",
            condition=Condition.TARGET_ONLY,
            system="system",
            user="user",
            template_version="test",
            prompt_sha256="abc",
        ),
    )


def test_openai_provider_rejects_non_http_endpoint() -> None:
    with pytest.raises(ValueError, match="http"):
        OpenAICompatibleProvider("file:///tmp/socket", "secret")


def test_openai_provider_extracts_text(monkeypatch) -> None:
    class Headers:
        def get(self, _name: str) -> str:
            return "req-1"

    class Response:
        headers = Headers()

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self) -> bytes:
            return (
                b'{"id":"completion-1","model":"served-model","choices":'
                b'[{"message":{"content":"ANSWER: ok"},"finish_reason":"stop"}],'
                b'"usage":{"prompt_tokens":10,"completion_tokens":3}}'
            )

    monkeypatch.setattr("mindsetbench.runner.providers.urlopen", lambda *_a, **_k: Response())
    provider = OpenAICompatibleProvider("https://example.test/v1/chat/completions", "secret")
    response = asyncio.run(provider.generate(_request()))
    assert response.text == "ANSWER: ok"
    assert response.model == "served-model"
    assert response.input_tokens == 10
    assert response.output_tokens == 3


def test_openai_provider_negotiates_completion_token_parameter(monkeypatch) -> None:
    payloads = []

    class Headers:
        def get(self, _name: str) -> str | None:
            return None

    class Response:
        headers = Headers()

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self) -> bytes:
            return b'{"choices":[{"message":{"content":"ANSWER: ok"}}]}'

    def fake_urlopen(request, **_kwargs):
        payload = json.loads(request.data)
        payloads.append(payload)
        if len(payloads) == 1:
            body = io.BytesIO(b'{"error":{"code":"unsupported_parameter","param":"max_tokens"}}')
            raise HTTPError(request.full_url, 400, "bad request", {}, body)
        return Response()

    monkeypatch.setattr("mindsetbench.runner.providers.urlopen", fake_urlopen)
    provider = OpenAICompatibleProvider("https://example.test/v1/chat/completions", "secret")
    response = asyncio.run(provider.generate(_request()))
    assert "max_tokens" in payloads[0]
    assert "max_completion_tokens" in payloads[1]
    assert response.raw_metadata["negotiated_parameters"] == ["max_tokens->max_completion_tokens"]

    second = asyncio.run(provider.generate(_request()))
    assert second.text == "ANSWER: ok"
    assert len(payloads) == 3
    assert "max_completion_tokens" in payloads[2]
