from __future__ import annotations

import os
from typing import Any, Final

import httpx

DEFAULT_BASE_URL: Final[str] = "https://api.microtensor.cloud/v1"
AUTO: Final[str] = "mt/auto"
TIMEOUT_SECONDS: Final[float] = 180.0
NO_KEY: Final[str] = (
    "set MICROTENSOR_API_KEY to a key from https://www.microtensor.cloud/console/keys"
)


class GatewayError(RuntimeError):
    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.code = code


def settings() -> tuple[str, str]:
    key = os.environ.get("MICROTENSOR_API_KEY", "").strip()
    base = os.environ.get("MICROTENSOR_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    return key, base


class Client:
    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not api_key:
            raise GatewayError(0, "missing_api_key", NO_KEY)
        self._http = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers={"authorization": f"Bearer {api_key}", "accept": "application/json"},
            timeout=TIMEOUT_SECONDS,
            transport=transport,
        )

    @classmethod
    def from_env(cls, *, transport: httpx.BaseTransport | None = None) -> Client:
        key, base = settings()
        return cls(key, base, transport=transport)

    def close(self) -> None:
        self._http.close()

    def _answer(self, response: httpx.Response) -> dict[str, Any]:
        try:
            body = response.json()
        except ValueError as exc:
            raise GatewayError(response.status_code, "bad_gateway", "not JSON") from exc
        if response.status_code >= 400:
            error = body.get("error") if isinstance(body, dict) else None
            error = error if isinstance(error, dict) else {}
            raise GatewayError(
                response.status_code,
                str(error.get("code", "error")),
                str(error.get("message", response.text[:200])),
            )
        if not isinstance(body, dict):
            raise GatewayError(response.status_code, "bad_gateway", "unexpected answer")
        return body

    def models(self) -> list[dict[str, Any]]:
        body = self._answer(self._http.get("/models"))
        return [dict(m) for m in body.get("data", [])]

    def chat(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        quality_floor: float | None = None,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"model": model, "messages": messages, "stream": False}
        if quality_floor is not None:
            payload["quality_floor"] = float(quality_floor)
        if max_tokens is not None:
            payload["max_tokens"] = int(max_tokens)
        return self._answer(self._http.post("/chat/completions", json=payload))


def messages_for(question: str, context: str = "") -> list[dict[str, str]]:
    found: list[dict[str, str]] = []
    if context.strip():
        found.append({"role": "system", "content": context})
    found.append({"role": "user", "content": question})
    return found


def summary_of(answer: dict[str, Any]) -> dict[str, Any]:
    choices = answer.get("choices") or [{}]
    message = choices[0].get("message") or {}
    routing = answer.get("routing") or {}
    served = answer.get("served_by") or {}
    usage = answer.get("usage") or {}
    return {
        "answer": str(message.get("content", "")),
        "task": routing.get("task", ""),
        "specialist": routing.get("specialist", answer.get("model", "")),
        "task_confidence": routing.get("task_confidence"),
        "answer_confidence": routing.get("answer_confidence"),
        "quality_floor": routing.get("quality_floor"),
        "floor_met": bool(routing.get("floor_met", False)),
        "verified": bool(routing.get("verified", False)),
        "operator": served.get("operator", ""),
        "latency_ms": served.get("latency_ms"),
        "tokens": usage.get("total_tokens"),
        "request_id": answer.get("id", ""),
    }
