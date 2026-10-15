# microtensor-mcp

An MCP server that gives Claude, ChatGPT, Microsoft Copilot, Cursor, VS Code and any other MCP host the Microtensor certified specialists as tools. Your API key stays in the server's environment; the agent only sees the tools.

## Tools

| Tool | What it does |
|---|---|
| `ask_specialist(question, context="", model="mt/auto", quality_floor=0.9)` | Sends the request to `mt/auto` or a named model and returns the answer with the routing block: task, specialist, confidences, whether the floor was met, the operator and the request id |
| `list_models()` | The models the API serves, with task, quality and whether an operator holds them now |
| `routing_tasks()` | The tasks `mt/auto` routes today and the specialist each one goes to |

`context` becomes the system message (for SQL, the schema as `CREATE TABLE` statements) and `question` the user message. Errors come back as `{error, message, status}` so the agent can decide what to do.

## Install

    pip install microtensor-mcp

or run it without installing:

    uvx microtensor-mcp

Set `MICROTENSOR_API_KEY` to a key from https://www.microtensor.cloud/console/keys. `MICROTENSOR_BASE_URL` overrides the API (default `https://api.microtensor.cloud/v1`).

## Claude Desktop

`claude_desktop_config.json` (macOS `~/Library/Application Support/Claude/`, Windows `%AppData%\Claude\`):

    {
      "mcpServers": {
        "microtensor": {
          "command": "uvx",
          "args": ["microtensor-mcp"],
          "env": { "MICROTENSOR_API_KEY": "mt_sk_..." }
        }
      }
    }

## Cursor and VS Code

Same shape. VS Code takes it in `.vscode/mcp.json` under `servers` with `"type": "stdio"`; Cursor under Settings → MCP.

## ChatGPT and Copilot

Both connect to MCP servers over HTTP. Run `microtensor-mcp --http --port 8765` behind your own HTTPS endpoint and register that URL.

## Development

    pip install -e ".[dev]"
    ruff check . && mypy microtensor_mcp && pytest -q

Docs: https://www.microtensor.cloud/docs/api/integrations/mcp
