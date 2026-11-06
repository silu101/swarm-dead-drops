"""Render what a monitor sees. Never includes system prompts.

Views (PREREG):
  actions    tool calls, tool results, visible notes        (primary)
  reasoning  actions + reasoning text where the model gave it (upper bound)
  stripped   tool calls and tool results only, no notes      (H6b)
The skeptical view (H6c) is the `actions` record with the skeptical judge prompt.
"""

from __future__ import annotations

import json

VIEWS = ("actions", "reasoning", "stripped")
MAX_FIELD = 1500  # characters per tool argument / result / note, to bound judge cost


def _clip(s: str) -> str:
    s = s if isinstance(s, str) else json.dumps(s)
    return s if len(s) <= MAX_FIELD else s[:MAX_FIELD] + f"... [{len(s) - MAX_FIELD} more characters]"


def _fmt_args(raw: str) -> str:
    try:
        args = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return _clip(raw)
    if not isinstance(args, dict):
        return _clip(raw)
    return ", ".join(f"{k}={json.dumps(_clip(v) if isinstance(v, str) else v)}" for k, v in args.items())


def render(ep: dict, view: str, agent: str | None = None) -> str:
    """One agent's record (agent=name) or the joint record (agent=None), in run order."""
    assert view in VIEWS
    results = {}
    for t in ep["tools"]:
        results[(t["agent"], t["turn"], t["tool_call_id"])] = t["result"]
    lines = []
    for c in ep["calls"]:
        if agent is not None and c["agent"] != agent:
            continue
        who = "" if agent is not None else f"{c['agent']} "
        lines.append(f"[{who}turn {c['turn']}]")
        if view == "reasoning" and c.get("reasoning"):
            lines.append(f"  reasoning: {_clip(str(c['reasoning']))}")
        if view != "stripped" and (c.get("content") or "").strip():
            lines.append(f"  note: {_clip(c['content'].strip())}")
        for tc in c.get("tool_calls", []):
            fn = tc["function"]
            lines.append(f"  -> {fn['name']}({_fmt_args(fn.get('arguments'))})")
            res = results.get((c["agent"], c["turn"], tc["id"]))
            if res is not None:
                lines.append(f"  <- {_clip(res)}")
    return "\n".join(lines)
