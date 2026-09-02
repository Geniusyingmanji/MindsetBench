from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Mapping
from pathlib import Path
from threading import Lock
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from mindsetbench.models.run import ModelRequest, ModelResponse


class Provider(Protocol):
    async def generate(self, request: ModelRequest) -> ModelResponse: ...


class ProviderError(RuntimeError):
    """A provider failure safe to surface without leaking credentials."""

    def __init__(self, message: str, *, retryable: bool = False):
        super().__init__(message)
        self.retryable = retryable


class OpenAICompatibleProvider:
    """Minimal async client for OpenAI-compatible chat completion endpoints."""

    def __init__(
        self,
        endpoint: str,
        api_key: str,
        *,
        timeout_seconds: float = 180.0,
        extra_headers: Mapping[str, str] | None = None,
    ):
        if not endpoint.startswith(("http://", "https://")):
            raise ValueError("endpoint must be an http(s) URL")
        if not api_key.strip():
            raise ValueError("api key must not be empty")
        self._endpoint = endpoint
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds
        self._extra_headers = dict(extra_headers or {})
        self._negotiation_lock = Lock()
        self._known_adaptations: list[str] = []

    async def generate(self, request: ModelRequest) -> ModelResponse:
        return await asyncio.to_thread(self._generate_sync, request)

    def _generate_sync(self, request: ModelRequest) -> ModelResponse:
        started = time.perf_counter()
        payload: dict[str, object] = {
            "model": request.model,
            "messages": [
                {"role": "system", "content": request.prompt.system},
                {"role": "user", "content": request.prompt.user},
            ],
            "temperature": request.temperature,
            "max_tokens": request.max_output_tokens,
        }
        if request.seed is not None:
            payload["seed"] = request.seed

        with self._negotiation_lock:
            known_adaptations = list(self._known_adaptations)
        for adaptation in known_adaptations:
            _apply_adaptation(payload, adaptation)
        raw, request_id, negotiated = self._post_with_negotiation(payload)

        try:
            data = json.loads(raw)
            choice = data["choices"][0]
            text = _message_text(choice["message"]["content"])
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise ProviderError(f"malformed provider response: {raw[:2000]}") from exc

        usage = data.get("usage") or {}
        return ModelResponse(
            text=text,
            model=str(data.get("model") or request.model),
            input_tokens=_optional_int(usage.get("prompt_tokens")),
            output_tokens=_optional_int(usage.get("completion_tokens")),
            latency_ms=int((time.perf_counter() - started) * 1000),
            provider_request_id=str(data.get("id") or request_id or "") or None,
            finish_reason=choice.get("finish_reason"),
            raw_metadata={
                "provider": "openai-compatible",
                "negotiated_parameters": [*known_adaptations, *negotiated],
            },
        )

    def _post_with_negotiation(
        self, payload: dict[str, object]
    ) -> tuple[str, str | None, list[str]]:
        negotiated: list[str] = []
        for _attempt in range(4):
            http_request = Request(
                self._endpoint,
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                method="POST",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                    "User-Agent": "MindsetBench/0.1",
                    **self._extra_headers,
                },
            )
            try:
                with urlopen(http_request, timeout=self._timeout_seconds) as response:
                    raw = response.read().decode("utf-8")
                    return raw, response.headers.get("x-request-id"), negotiated
            except HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")[:2000]
                adaptation = _adapt_unsupported_parameter(payload, exc.code, detail)
                if adaptation:
                    with self._negotiation_lock:
                        if adaptation not in self._known_adaptations:
                            self._known_adaptations.append(adaptation)
                    negotiated.append(adaptation)
                    continue
                retryable = exc.code in {408, 409, 425, 429} or exc.code >= 500
                raise ProviderError(
                    f"provider HTTP {exc.code}: {detail}",
                    retryable=retryable,
                ) from exc
            except URLError as exc:
                raise ProviderError(
                    f"provider connection failed: {exc.reason}",
                    retryable=True,
                ) from exc
        raise ProviderError("provider parameter negotiation did not converge")


class MockProvider:
    """Deterministic provider for smoke tests and offline protocol development."""

    def __init__(self, responses: Mapping[str, str], *, default: str | None = None):
        self._responses = dict(responses)
        self._default = default
        self.call_count = 0

    async def generate(self, request: ModelRequest) -> ModelResponse:
        started = time.perf_counter()
        self.call_count += 1
        case_id = request.prompt.case_id
        condition = request.prompt.condition.value
        sample_index = request.metadata.get("sample_index", 0)
        keys = (
            f"{case_id}|{condition}|{sample_index}",
            f"{case_id}|{condition}",
            case_id,
        )
        text = next((self._responses[key] for key in keys if key in self._responses), self._default)
        if text is None:
            raise KeyError(f"mock response not configured for {keys[0]}")
        return ModelResponse(
            text=text,
            model=request.model,
            latency_ms=int((time.perf_counter() - started) * 1000),
            finish_reason="stop",
            raw_metadata={"provider": "mock"},
        )


class ReplayProvider(MockProvider):
    """Replay responses from JSONL without making network calls."""

    @classmethod
    def from_jsonl(cls, path: str | Path) -> ReplayProvider:
        responses: dict[str, str] = {}
        with Path(path).open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                row = json.loads(line)
                case_id = row.get("case_id") or row.get("id")
                condition = row.get("condition") or row.get("cond")
                if not case_id or not condition:
                    raise ValueError(f"replay row {line_number} lacks case id or condition")
                sample_index = row.get("sample_index", 0)
                text = _response_text(row)
                responses[f"{case_id}|{condition}|{sample_index}"] = text
        return cls(responses)


def _response_text(row: dict) -> str:
    response = row.get("response")
    if isinstance(response, str):
        return response
    if isinstance(response, dict) and isinstance(response.get("text"), str):
        return response["text"]
    if row.get("pred") is not None:
        return f"ANSWER: {row['pred']}"
    raise ValueError("replay row has no response text or prediction")


def _message_text(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        chunks = [
            part.get("text", "")
            for part in content
            if isinstance(part, dict) and part.get("type") in {"text", "output_text"}
        ]
        if chunks:
            return "".join(chunks)
    raise TypeError("message content is not text")


def _optional_int(value: object) -> int | None:
    return int(value) if isinstance(value, int | float) else None


def _adapt_unsupported_parameter(
    payload: dict[str, object], status: int, detail: str
) -> str | None:
    if status != 400:
        return None
    try:
        parameter = json.loads(detail).get("error", {}).get("param")
    except (AttributeError, json.JSONDecodeError):
        return None
    if parameter == "max_tokens" and "max_tokens" in payload:
        adaptation = "max_tokens->max_completion_tokens"
        _apply_adaptation(payload, adaptation)
        return adaptation
    if parameter in {"temperature", "seed"} and parameter in payload:
        adaptation = f"dropped-{parameter}"
        _apply_adaptation(payload, adaptation)
        return adaptation
    return None


def _apply_adaptation(payload: dict[str, object], adaptation: str) -> None:
    if adaptation == "max_tokens->max_completion_tokens" and "max_tokens" in payload:
        payload["max_completion_tokens"] = payload.pop("max_tokens")
    elif adaptation.startswith("dropped-"):
        payload.pop(adaptation.removeprefix("dropped-"), None)
