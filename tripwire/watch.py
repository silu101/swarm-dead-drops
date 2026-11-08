"""Folder watcher: the easy option when you can't wrap the agents' tools.

It polls a directory and logs file creates, edits and deletes. **It cannot see reads, or which agent did what**: events carry agent "?" unless `attribute` maps a path to an owner. So the dead-drop flag (written, read by another agent, deleted) can't fire; you only get short-lived-file and other content flags. Standard library only (no watchdog).
"""

from __future__ import annotations

import hashlib
import os
import time
from pathlib import Path
from typing import Callable

from .events import EventLog


def snapshot(root: Path) -> dict[str, str]:
    out = {}
    for dirpath, _, files in os.walk(root):
        for f in files:
            p = Path(dirpath) / f
            try:
                out["/" + str(p.relative_to(root))] = hashlib.sha256(p.read_bytes()).hexdigest()
            except OSError:
                pass
    return out


def watch(root: str, log: EventLog, interval: float = 0.5, stop: Callable[[], bool] | None = None,
          attribute: Callable[[str], str] | None = None, max_chars: int = 200_000) -> None:
    rootp = Path(root).resolve()
    who = attribute or (lambda path: "?")
    prev = snapshot(rootp)
    for path in sorted(prev):
        log.append(op="seed", agent="_setup", path=path, content=_text(rootp, path, max_chars), source="watcher")
    while not (stop and stop()):
        time.sleep(interval)
        cur = snapshot(rootp)
        for path in sorted(cur):
            if prev.get(path) != cur[path]:
                log.append(op="write", agent=who(path), path=path, content=_text(rootp, path, max_chars), source="watcher")
        for path in sorted(set(prev) - set(cur)):
            log.append(op="delete", agent=who(path), path=path, source="watcher")
        prev = cur


def _text(root: Path, path: str, max_chars: int) -> str | None:
    try:
        return (root / path.lstrip("/")).read_text(encoding="utf-8", errors="replace")[:max_chars]
    except OSError:
        return None
