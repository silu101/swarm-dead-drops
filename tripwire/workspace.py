"""Tool-layer wrapper: logged file tools over a real shared directory.

Give each agent these tools instead of raw file access. Every read, write, list and delete is logged with the agent's name, so the log sees reads (a folder watcher can't).

    ws = Workspace("/tmp/team", log="/tmp/team.events.jsonl")
    ws.write("ava", "notes/plan.md", "hello", turn=1)
    ws.read("ben", "notes/plan.md", turn=2)
    ws.note("ben", "read ava's plan", turn=2)   # optional: agents' visible notes

For OpenAI-style tool calling, `TOOL_SCHEMAS` and `ws.dispatch(agent, name, args_json)` cover the four tools.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from .events import EventLog
from .guard import Guard

MAX_FILE_CHARS = 200_000


class WorkspaceError(Exception):
    pass


class Workspace:
    def __init__(self, root: str, log: str | EventLog | None = None, guard: Guard | None = None):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.log = log if isinstance(log, EventLog) else EventLog(log)
        self.guard = guard
        if guard:
            for f in self.root.rglob("*"):
                if f.is_file():
                    guard.adopt(self._rel(f))

    def _guard(self, d, turn, content=None):
        """Log a guard decision; raise if it blocks."""
        if d is None:
            return
        self.log.append(op="guard", agent=d.agent, path=d.path, turn=turn, ok=d.allowed,
                        error=None if d.allowed else d.reason,
                        content=json.dumps({"reason": d.reason, **d.info, "proposed": None if d.allowed else content}))
        if not d.allowed:
            raise WorkspaceError(d.reason)

    def _real(self, path: str) -> Path:
        if not isinstance(path, str) or not path.strip():
            raise WorkspaceError("path must be a non-empty string")
        p = (self.root / path.strip().lstrip("/")).resolve()
        if p != self.root and self.root not in p.parents:
            raise WorkspaceError("path is outside the workspace")
        return p

    def _rel(self, p: Path) -> str:
        return "/" + str(p.relative_to(self.root)) if p != self.root else "/"

    def _do(self, agent, op, path, turn, fn, content=None):
        try:
            p = self._real(path)
            result = fn(p)
        except (WorkspaceError, OSError) as e:
            self.log.append(op=op, agent=agent, path=str(path), turn=turn, ok=False, error=str(e), content=content)
            raise WorkspaceError(str(e)) from e
        self.log.append(op=op, agent=agent, path=self._rel(p), turn=turn, content=content)
        return result

    def read(self, agent: str, path: str, turn: int | None = None) -> str:
        return self._do(agent, "read", path, turn, lambda p: p.read_text(encoding="utf-8"))

    def write(self, agent: str, path: str, content: str, turn: int | None = None) -> str:
        if not isinstance(content, str) or len(content) > MAX_FILE_CHARS:
            raise WorkspaceError("content must be a string under the size limit")

        if self.guard:
            try:
                p = self._real(path)
            except WorkspaceError:
                p = None  # bad path: let _do log and raise it
            if p is not None:
                old = p.read_text(encoding="utf-8") if p.is_file() else None
                self._guard(self.guard.check_write(agent, self._rel(p), old, content), turn, content)

        def fn(p: Path):
            if p.is_dir():
                raise WorkspaceError("path is a folder")
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            return f"wrote {len(content)} characters"

        return self._do(agent, "write", path, turn, fn, content=content)

    def list(self, agent: str, path: str = "/", turn: int | None = None) -> list[str]:
        def fn(p: Path):
            return sorted(self._rel(c) + ("/" if c.is_dir() else "") for c in p.iterdir())

        return self._do(agent, "list", path, turn, fn)

    def delete(self, agent: str, path: str, turn: int | None = None) -> str:
        if self.guard:
            try:
                rel = self._rel(self._real(path))
            except WorkspaceError:
                rel = None
            if rel:
                self._guard(self.guard.check_delete(agent, rel), turn)

        def fn(p: Path):
            if not p.is_file():
                raise WorkspaceError("no such file")
            os.remove(p)
            return "deleted"

        return self._do(agent, "delete", path, turn, fn)

    def note(self, agent: str, text: str, turn: int | None = None) -> None:
        """Record an agent's visible note/message. Used to check whether agents mention the files they pass around."""
        self.log.append(op="note", agent=agent, turn=turn, content=text)

    def dispatch(self, agent: str, name: str, args: str | dict, turn: int | None = None) -> str:
        """Run one OpenAI-style tool call; errors come back as text for the model."""
        try:
            a = json.loads(args) if isinstance(args, str) else dict(args or {})
            if name == "read_file":
                return self.read(agent, a["path"], turn)
            if name == "write_file":
                return self.write(agent, a["path"], a["content"], turn)
            if name == "list_files":
                return "\n".join(self.list(agent, a.get("path", "/"), turn))
            if name == "delete_file":
                return self.delete(agent, a["path"], turn)
            return f"error: unknown tool {name}"
        except (WorkspaceError, KeyError, ValueError, TypeError) as e:
            return f"error: {e}"


def _fn(name, desc, props, req):
    return {"type": "function", "function": {"name": name, "description": desc,
            "parameters": {"type": "object", "properties": props, "required": req}}}


_PATH = {"path": {"type": "string"}}
TOOL_SCHEMAS = [
    _fn("read_file", "Read a file in the shared workspace.", _PATH, ["path"]),
    _fn("write_file", "Create or overwrite a file.", {**_PATH, "content": {"type": "string"}}, ["path", "content"]),
    _fn("list_files", "List a folder.", _PATH, []),
    _fn("delete_file", "Delete a file.", _PATH, ["path"]),
]
