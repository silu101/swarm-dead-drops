"""In-memory filesystem for one episode, with an append-only audit log.

Agents reach files only through the four tools in tools.py, so the audit log
(held here, written to the episode JSONL) is outside their reach by design.

Layout seen by agent `name`:
  /home/<name>/...   private; only that agent can read or write it
  /shared/...        SHARED mode: one folder for everyone
                     ISOLATED mode: each agent gets its own private copy
"""

from __future__ import annotations

import posixpath
from dataclasses import dataclass, field
from typing import Callable


class FSError(Exception):
    pass


@dataclass
class AuditEvent:
    seq: int
    turn: int
    agent: str
    op: str  # read | write | list | delete
    path: str  # agent-visible path
    real_path: str  # namespaced path (differs from `path` only in ISOLATED mode)
    ok: bool
    error: str | None = None
    content: str | None = None  # full content for writes, so any past state can be rebuilt

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


MAX_FILE_CHARS = 20_000


@dataclass
class VirtualFS:
    agents: list[str]
    isolated: bool = False
    files: dict[str, str] = field(default_factory=dict)  # real_path -> content
    audit: list[AuditEvent] = field(default_factory=list)
    on_event: Callable[[AuditEvent], None] | None = None

    # ---- path handling -------------------------------------------------
    def _norm(self, path: str) -> str:
        if not isinstance(path, str) or not path.strip():
            raise FSError("path must be a non-empty string")
        p = posixpath.normpath("/" + path.strip().lstrip("/"))
        return p

    def _resolve(self, agent: str, path: str) -> str:
        """Return the real (namespaced) path, or raise FSError if not allowed."""
        p = self._norm(path)
        if p == "/shared" or p.startswith("/shared/"):
            if self.isolated:
                return f"/_iso/{agent}{p}"
            return p
        home = f"/home/{agent}"
        if p == home or p.startswith(home + "/"):
            return p
        if p.startswith("/home/"):
            raise FSError("permission denied")
        raise FSError("only /shared and your home folder are available")

    def _log(self, turn, agent, op, path, real, ok, error=None, content=None):
        ev = AuditEvent(len(self.audit), turn, agent, op, path, real, ok, error, content)
        self.audit.append(ev)
        if self.on_event:
            self.on_event(ev)

    # ---- tools -----------------------------------------------------------
    def read(self, agent: str, path: str, turn: int) -> str:
        try:
            real = self._resolve(agent, path)
            if real not in self.files:
                raise FSError("no such file")
        except FSError as e:
            self._log(turn, agent, "read", str(path), "", False, str(e))
            raise
        self._log(turn, agent, "read", self._norm(path), real, True)
        return self.files[real]

    def write(self, agent: str, path: str, content: str, turn: int) -> str:
        try:
            real = self._resolve(agent, path)
            if not isinstance(content, str):
                raise FSError("content must be a string")
            if len(content) > MAX_FILE_CHARS:
                raise FSError(f"file too large (max {MAX_FILE_CHARS} characters)")
            if real.endswith("/") or any(k.startswith(real + "/") for k in self.files):
                raise FSError("path is a folder")
        except FSError as e:
            self._log(turn, agent, "write", str(path), "", False, str(e), content if isinstance(content, str) else None)
            raise
        self.files[real] = content
        self._log(turn, agent, "write", self._norm(path), real, True, content=content)
        return f"wrote {len(content)} characters to {self._norm(path)}"

    def list(self, agent: str, path: str, turn: int) -> list[str]:
        try:
            real = self._resolve(agent, path)
        except FSError as e:
            self._log(turn, agent, "list", str(path), "", False, str(e))
            raise
        prefix = real.rstrip("/") + "/"
        vis_prefix = self._norm(path).rstrip("/") + "/"
        out = set()
        for k in self.files:
            if k.startswith(prefix):
                rest = k[len(prefix):]
                head = rest.split("/", 1)
                out.add(vis_prefix + head[0] + ("/" if len(head) > 1 else ""))
        self._log(turn, agent, "list", self._norm(path), real, True)
        return sorted(out)

    def delete(self, agent: str, path: str, turn: int) -> str:
        try:
            real = self._resolve(agent, path)
            if real not in self.files:
                raise FSError("no such file")
        except FSError as e:
            self._log(turn, agent, "delete", str(path), "", False, str(e))
            raise
        del self.files[real]
        self._log(turn, agent, "delete", self._norm(path), real, True)
        return f"deleted {self._norm(path)}"

    # ---- setup (not logged as agent actions) -----------------------------
    def seed_file(self, real_path: str, content: str) -> None:
        """Place a starting file. Logged as op 'seed' (agent '_setup', turn -1)
        so the audit log alone can rebuild the full state at any point."""
        self.files[real_path] = content
        self._log(-1, "_setup", "seed", real_path, real_path, True, content=content)
