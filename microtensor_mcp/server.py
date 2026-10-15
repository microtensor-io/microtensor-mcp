from __future__ import annotations

import argparse
from typing import Any

from mcp.server.fastmcp import FastMCP

from microtensor_mcp.client import AUTO, Client, GatewayError, messages_for, summary_of

mcp = FastMCP(
    "microtensor",
    instructions=(
        "Tools for the Microtensor API. ask_specialist answers one task with a certified "
        "specialist and reports its confidence; list_models and routing_tasks say what is served."
    ),
)


def _error(exc: GatewayError) -> dict[str, Any]:
    return {"error": exc.code, "message": str(exc), "status": exc.status}


@mcp.tool(
    description=(
        "Send a request to a Microtensor specialist. context is the task context (for SQL, "
        "the schema as CREATE TABLE statements); model is mt/auto, mt/<arena> or a pin."
    )
)
def ask_specialist(
    question: str, context: str = "", model: str = AUTO, quality_floor: float = 0.9
) -> dict[str, Any]:
    try:
        client = Client.from_env()
        try:
            answer = client.chat(
                model=model, messages=messages_for(question, context), quality_floor=quality_floor
            )
        finally:
            client.close()
    except GatewayError as exc:
        return _error(exc)
    return summary_of(answer)


@mcp.tool(
    description="List the served models with task, quality and whether an operator holds them now."
)
def list_models() -> list[dict[str, Any]]:
    try:
        client = Client.from_env()
        try:
            models = client.models()
        finally:
            client.close()
    except GatewayError as exc:
        return [_error(exc)]
    return [
        {
            "id": m.get("id"),
            "task": m.get("task", ""),
            "quality": m.get("quality"),
            "live": bool((m.get("capacity") or {}).get("live", False)),
            "operators": (m.get("capacity") or {}).get("operators", 0),
        }
        for m in models
        if m.get("id") != AUTO
    ]


@mcp.tool(description="List the tasks mt/auto routes today and the specialist each one goes to.")
def routing_tasks() -> list[dict[str, Any]]:
    try:
        client = Client.from_env()
        try:
            models = client.models()
        finally:
            client.close()
    except GatewayError as exc:
        return [_error(exc)]
    auto = next((m for m in models if m.get("id") == AUTO), {})
    return [dict(t) for t in auto.get("tasks", [])]


def main() -> None:
    parser = argparse.ArgumentParser(prog="microtensor-mcp")
    parser.add_argument("--http", action="store_true", help="serve over streamable HTTP")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    if args.http:
        mcp.settings.host = args.host
        mcp.settings.port = args.port
        mcp.run(transport="streamable-http")
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
