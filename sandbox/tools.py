"""The four file tools agents get (OpenAI/OpenRouter function-calling format)."""

from __future__ import annotations

import json

from .fs import FSError, VirtualFS

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read",
            "description": "Read a file and return its contents.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "Absolute path, e.g. /shared/MIGRATION.md"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write",
            "description": "Create or overwrite a file with the given contents.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Absolute path, e.g. /shared/migrated/ledger.yaml"},
                    "content": {"type": "string", "description": "Full file contents."},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list",
            "description": "List the files and folders inside a folder.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "Folder path, e.g. /shared"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete",
            "description": "Delete a file.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
    },
]


def run_tool(fs: VirtualFS, agent: str, turn: int, name: str, raw_args: str | dict) -> tuple[str, bool]:
    """Execute one tool call. Returns (result text shown to the agent, ok).

    ok=False marks a *malformed* call (bad JSON, unknown tool, missing args): these
    count toward the pilot's tool-call error rate. A well-formed call that fails
    normally (e.g. file not found) returns ok=True with an error message.
    """
    try:
        args = raw_args if isinstance(raw_args, dict) else json.loads(raw_args or "{}")
        if not isinstance(args, dict):
            raise ValueError("arguments must be a JSON object")
    except (ValueError, TypeError) as e:
        return f"error: could not parse arguments ({e})", False
    try:
        if name == "read":
            return fs.read(agent, args["path"], turn), True
        if name == "write":
            return fs.write(agent, args["path"], args["content"], turn), True
        if name == "list":
            items = fs.list(agent, args.get("path", "/shared"), turn)
            return ("\n".join(items) if items else "(empty)"), True
        if name == "delete":
            return fs.delete(agent, args["path"], turn), True
        return f"error: unknown tool '{name}'", False
    except KeyError as e:
        return f"error: missing argument {e}", False
    except FSError as e:
        return f"error: {e}", True
