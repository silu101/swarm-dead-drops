"""Append-only, hash-chained event log.

Each line is one JSON event and carries the sha256 of the previous line. If anyone edits or deletes an earlier line, `verify()` reports the first break.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from dataclasses import asdict, dataclass, field

OPS = ("read", "write", "list", "delete", "note", "seed")


@dataclass
class Event:
    seq: int
    op: str  # read | write | list | delete | note | seed
    agent: str  # "?" when the source can't tell (folder watcher)
    path: str = ""
    content: str | None = None  # full text for writes and notes
    turn: int | None = None
    ts: float = field(default_factory=time.time)
    ok: bool = True
    error: str | None = None
    source: str = "wrapper"  # wrapper | watcher | import
    prev: str = ""  # sha256 of the previous log line

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, sort_keys=True)


class EventLog:
    """Append events to a JSONL file (fsync after each write) and keep them in memory."""

    def __init__(self, path: str | None = None):
        self.path = path
        self.events: list[Event] = []
        self._lock = threading.Lock()
        self._last = ""
        if path and os.path.exists(path):
            for ev in load(path):
                self.events.append(ev)
            with open(path, "rb") as f:
                lines = f.read().splitlines()
            self._last = hashlib.sha256(lines[-1]).hexdigest() if lines else ""

    def append(self, **kw) -> Event:
        with self._lock:
            ev = Event(seq=len(self.events), prev=self._last, **kw)
            line = ev.to_json()
            self._last = hashlib.sha256(line.encode()).hexdigest()
            self.events.append(ev)
            if self.path:
                with open(self.path, "a", encoding="utf-8") as f:
                    f.write(line + "\n")
                    f.flush()
                    os.fsync(f.fileno())
            return ev


def load(path: str) -> list[Event]:
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                out.append(Event(**json.loads(line)))
    return out


def verify(path: str) -> tuple[bool, int | None]:
    """Check the hash chain. Returns (ok, line number of the first break or None)."""
    prev = ""
    with open(path, "rb") as f:
        for i, raw in enumerate(f.read().splitlines()):
            if not raw.strip():
                continue
            if json.loads(raw).get("prev", "") != prev:
                return False, i + 1
            prev = hashlib.sha256(raw).hexdigest()
    return True, None
