from __future__ import annotations

import json

import httpx
import pytest

from microtensor_mcp.client import Client, GatewayError, messages_for, summary_of


def gateway(request: httpx.Request) -> httpx.Response:
    if request.url.path.endswith("/models"):
        return httpx.Response(
            200,
            json={
                "data": [
                    {
                        "id": "mt/auto",
                        "tasks": [
                            {"task": "sql_generation", "model": "mt/sql_gen_s1", "live": True}
                        ],
                    },
                    {
                        "id": "mt/sql_gen_s1",
                        "task": "sql_generation",
                        "quality": 0.73,
                        "capacity": {"operators": 2, "live": True},
                    },
                ]
            },
        )
    body = json.loads(request.content)
    if body["model"] == "mt/none":
        return httpx.Response(
            404, json={"error": {"code": "model_not_found", "message": "no", "type": "x"}}
        )
    return httpx.Response(
        200,
        json={
            "id": "cmpl_1",
            "model": "mt/sql_gen_s1",
            "choices": [{"message": {"role": "assistant", "content": "SELECT 1"}}],
            "routing": {
                "task": "sql_generation",
                "specialist": "mt/sql_gen_s1",
                "answer_confidence": 0.96,
                "floor_met": True,
                "verified": True,
            },
            "served_by": {"operator": "5F", "latency_ms": 800},
            "usage": {"total_tokens": 49},
        },
    )


def test_the_client_answers_and_summarises() -> None:
    client = Client("mt_sk_x", "http://gateway/v1", transport=httpx.MockTransport(gateway))
    answer = client.chat(
        model="mt/auto", messages=messages_for("count", "CREATE TABLE t(x)"), quality_floor=0.9
    )
    found = summary_of(answer)
    assert found["answer"] == "SELECT 1" and found["floor_met"] and found["request_id"] == "cmpl_1"
    assert [m["id"] for m in client.models()] == ["mt/auto", "mt/sql_gen_s1"]
    with pytest.raises(GatewayError) as caught:
        client.chat(model="mt/none", messages=messages_for("x"))
    assert caught.value.code == "model_not_found" and caught.value.status == 404


def test_a_missing_key_is_refused_before_any_request() -> None:
    with pytest.raises(GatewayError) as caught:
        Client("")
    assert caught.value.code == "missing_api_key"
    assert messages_for("q") == [{"role": "user", "content": "q"}]
