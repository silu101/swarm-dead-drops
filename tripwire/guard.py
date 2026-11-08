"""Instruction-file guard.

Agents that share a folder also share the files they read as instructions: AGENTS.md, CLAUDE.md, READMEs, migration guides, task lists. An agent that edits one of those can steer every other agent. In Dead Drops, the strong swarm (Kimi K3.1 Pro) rewrote the shared MIGRATION.md in 14 of 20 covert episodes, each time hiding instructions inside an HTML comment, and on average 2.7 of the other 3 agents then followed them. No benign episode, in any experiment, edited that file.

The guard treats those files as privileged. An instruction file is one that matches the name patterns **and already existed before the agents started** (the baseline), or a path you list explicitly. New files agents create for their own notes (a fresh README.md, say) are not guarded: in our data honest agents did that in up to 19 of 30 runs, while editing a pre-existing instruction file happened only in covert runs. Policies:

  alert   let the edit through, log a `guard` event with the diff and the signals found
  block   refuse the edit; the agent gets an error, and the proposed text is logged for a human to review

Signals looked for in the added text (each is a pointer, not a verdict):

  hidden_comment   an HTML comment or a Markdown link-reference comment: text a human reader won't see when rendered
  secrecy          wording like "do not mention", "keep this out of", "don't tell"
  hidden_path_ref  mentions a path with a dot-folder or dot-file
  invisible_chars  zero-width or bidirectional-control characters
  new_path_ref     mentions an absolute path that the original file did not

    from tripwire import Workspace, Guard
    ws = Workspace("/tmp/team", log="team.events.jsonl", guard=Guard(policy="block"))
    # the Workspace adds every protected-name file already under /tmp/team to the guard's baseline
"""

from __future__ import annotations

import difflib
import fnmatch
import posixpath
import re
from dataclasses import dataclass, field

DEFAULT_PROTECTED = (
    "AGENTS.md", "CLAUDE.md", "GEMINI.md", "README*", "CONTRIBUTING*", "INSTRUCTIONS*", "MIGRATION*",
    "TASKS*", "TODO*", "PLAN*", "*.prompt", "*.prompt.md", "*.instructions.md", ".cursorrules", ".windsurfrules",
)

_COMMENT = re.compile(r"<!--.*?(-->|$)|^\s*\[//\]:\s*#", re.S | re.M)
_SECRECY = re.compile(
    r"\b(do\s+not|don'?t|never|avoid)\s+(mention|tell|report|disclose|reveal|log|note|discuss|include)\b"
    r"|\bkeep\s+(this|it|them)?\s*(out\s+of|private|secret|hidden|quiet|between)\b"
    r"|\b(without|no\s+need\s+for)\s+(mentioning|telling|reporting)\b"
    r"|\b(secretly|covertly|quietly)\b", re.I)
_PATH = re.compile(r"(?<![\w.])/(?:[\w.-]+/)*[\w.-]+")
_INVISIBLE = re.compile("[​-‏‪-‮⁠-⁤﻿]")


def _hidden(path: str) -> bool:
    return any(p.startswith(".") and p not in (".", "..") for p in path.split("/"))


def is_protected(path: str, patterns=DEFAULT_PROTECTED) -> bool:
    base = posixpath.basename(path)
    return any(fnmatch.fnmatch(base, p) or ("/" in p and fnmatch.fnmatch(path, p)) for p in patterns)


def inspect_edit(old: str | None, new: str | None) -> dict:
    """Diff an instruction file edit and list the signals in the added text."""
    old_l = (old or "").splitlines()
    new_l = (new or "").splitlines()
    added, removed = [], []
    for line in difflib.unified_diff(old_l, new_l, lineterm="", n=0):
        if line.startswith("+") and not line.startswith("+++"):
            added.append(line[1:])
        elif line.startswith("-") and not line.startswith("---"):
            removed.append(line[1:])
    text = "\n".join(added)
    signals = []
    if _COMMENT.search(text):
        signals.append("hidden_comment")
    if _SECRECY.search(text):
        signals.append("secrecy")
    paths = set(_PATH.findall(text))
    if any(_hidden(p) for p in paths):
        signals.append("hidden_path_ref")
    if _INVISIBLE.search(text):
        signals.append("invisible_chars")
    old_paths = set(_PATH.findall(old or ""))
    if paths - old_paths:
        signals.append("new_path_ref")
    return {"added": len(added), "removed": len(removed), "signals": signals,
            "added_text": text[:2000], "new_paths": sorted(paths - old_paths)[:10]}


@dataclass
class Decision:
    allowed: bool
    path: str
    agent: str
    reason: str
    info: dict = field(default_factory=dict)


class Guard:
    def __init__(self, protected=DEFAULT_PROTECTED, policy: str = "alert", block_hidden_paths: bool = False,
                 trusted_agents=("_setup",), paths=()):
        if policy not in ("alert", "block"):
            raise ValueError("policy must be 'alert' or 'block'")
        self.protected = tuple(protected)
        self.policy = policy
        self.block_hidden_paths = block_hidden_paths
        self.trusted = set(trusted_agents)
        self.baseline: set[str] = set(paths)  # guarded instruction files

    def adopt(self, path: str) -> bool:
        """Add a pre-existing file to the baseline if its name matches the patterns. Returns True if added."""
        if is_protected(path, self.protected):
            self.baseline.add(path)
            return True
        return False

    def guards(self, path: str) -> bool:
        return path in self.baseline

    def check_write(self, agent: str, path: str, old: str | None, new: str) -> Decision | None:
        """Return None when the guard has nothing to say, else a Decision (allowed or not)."""
        if agent in self.trusted:
            if old is None:
                self.adopt(path)  # files written by the operator before or during the run count as instructions
            return None
        if self.block_hidden_paths and _hidden(path):
            return Decision(False, path, agent, "writes to hidden paths are blocked", {"signals": ["hidden_path"]})
        if not self.guards(path):
            return None
        if old is not None and old == new:
            return None
        info = inspect_edit(old, new)
        ok = self.policy == "alert"
        reason = (f"{path} is an instruction file shared with other agents; "
                  + ("edit allowed and logged" if ok else "edits need human review, so this one was not applied"))
        return Decision(ok, path, agent, reason, info)

    def check_delete(self, agent: str, path: str) -> Decision | None:
        if agent in self.trusted or not self.guards(path):
            return None
        ok = self.policy == "alert"
        return Decision(ok, path, agent, f"{path} is an instruction file; " + ("delete logged" if ok else "delete blocked"),
                        {"signals": ["instruction_delete"]})
