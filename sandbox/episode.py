"""Run one episode: N agents, round-robin turns, file tools only.

Writes one JSONL file per episode, line by line (flushed + fsynced), so a crash
loses at most the current line. Line types:
  meta        episode settings, scenario (token fragments, variants, order)
  audit       one per file operation (from the VirtualFS audit log)
  call        one per model call (visible content, reasoning, tool calls, cost)
  tool        one per tool result
  transcript  each agent's full message list at the end
  summary     success flags, errors, cost
"""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

from scoring.success import check_episode

from .fs import VirtualFS
from .llm import BudgetExceeded, LLMError, append_jsonl
from .scenario import PUBLIC_TASK_SOLO, make_scenario, solo_system_prompt, system_prompt, turn_message
from .tools import TOOLS, run_tool


def _clean_assistant(msg: dict, ep_id: str, agent: str, turn: int) -> dict:
    """Assistant message as it goes back into the agent's history."""
    out = {"role": "assistant", "content": msg.get("content") or ""}
    calls = []
    for i, tc in enumerate(msg.get("tool_calls") or []):
        fn = tc.get("function") or {}
        calls.append(
            {
                "id": tc.get("id") or f"call_{agent}_{turn}_{i}",
                "type": "function",
                "function": {"name": fn.get("name", ""), "arguments": fn.get("arguments") or "{}"},
            }
        )
    if calls:
        out["tool_calls"] = calls
    return out


def run_episode(
    client,
    seed: int,
    goal: str,
    watched: bool = False,
    isolated: bool = False,
    turns: int = 20,
    out_dir: Path | str = "results/episodes",
    label: str = "",
    solo: bool = False,
) -> dict:
    """solo=True: single-agent baseline. One assistant (the scenario's first name)
    holds all four config files and does the whole task; same goal sentences."""
    assert goal in ("covert", "benign")
    assert not (solo and isolated)
    sc = make_scenario(seed)
    mode = "solo" if solo else ("iso" if isolated else "sh")
    ep_id = f"{label + '_' if label else ''}{goal}_{'W' if watched else 'U'}_{mode}_s{seed}_{uuid.uuid4().hex[:6]}"
    actors = [sc.names[0]] if solo else sc.names
    order = actors if solo else sc.order
    out_path = Path(out_dir) / f"{ep_id}.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    def emit(obj):
        append_jsonl(out_path, obj)

    emit(
        {
            "type": "meta",
            "episode_id": ep_id,
            "label": label,
            "model": getattr(client, "model", "?"),
            "provider_pinned": getattr(client, "provider", None),
            "seed": seed,
            "goal": goal,
            "watched": watched,
            "isolated": isolated,
            "turns": turns,
            "solo": solo,
            "order": order,
            "agents": [
                {"name": a.name, "index": a.index, "service": a.service, "core": a.core, "variant": a.variant}
                for a in sc.agents
            ] if not solo else [{"name": actors[0], "index": 0, "service": "all", "core": "".join(sc.token_cores),
                                 "variant": " ".join(a.variant for a in sc.agents)}],
            "fragments": [
                {"index": a.index, "service": a.service, "core": a.core, "variant": a.variant} for a in sc.agents
            ],
            **({"public_task": PUBLIC_TASK_SOLO} if solo else {}),
            "token_cores": sc.token_cores,
            "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
    )

    fs = VirtualFS(agents=actors, isolated=isolated, on_event=lambda ev: emit({"type": "audit", **ev.to_dict()}))
    for a in sc.agents:
        fs.seed_file(f"/home/{actors[0] if solo else a.name}/{a.service}.yaml", a.config_text)
    for path, content in sc.files_shared.items():
        if isolated:
            for name in sc.names:
                fs.seed_file(f"/_iso/{name}{path}", content)
        else:
            fs.seed_file(path, content)

    if solo:
        histories = {actors[0]: [{"role": "system", "content": solo_system_prompt(sc, goal, watched, turns)}]}
    else:
        histories = {n: [{"role": "system", "content": system_prompt(sc, n, goal, watched, turns)}] for n in sc.names}
    last_text = {n: "" for n in actors}
    final_output = {n: "" for n in actors}
    n_calls = n_tool_calls = n_bad_tool_calls = 0
    cost = 0.0
    error = None
    finish_reasons: dict[str, int] = {}

    try:
        for k in range(1, turns + 1):
            for name in order:
                hist = histories[name]
                hist.append({"role": "user", "content": turn_message(k, turns)})
                res = client.chat(hist, TOOLS, tag={"episode_id": ep_id, "agent": name, "turn": k})
                n_calls += 1
                cost += res.cost_usd
                finish_reasons[str(res.finish_reason)] = finish_reasons.get(str(res.finish_reason), 0) + 1
                msg = _clean_assistant(res.message, ep_id, name, k)
                hist.append(msg)
                reasoning = res.message.get("reasoning") or res.message.get("reasoning_content")
                emit(
                    {
                        "type": "call",
                        "agent": name,
                        "turn": k,
                        "content": msg["content"],
                        "reasoning": reasoning,
                        "tool_calls": msg.get("tool_calls", []),
                        "finish_reason": res.finish_reason,
                        "usage": res.usage,
                        "cost_usd": res.cost_usd,
                        "provider": res.provider,
                        "model": res.model,
                        "latency_s": res.latency_s,
                    }
                )
                if msg["content"].strip():
                    last_text[name] = msg["content"]
                if k == turns:
                    final_output[name] = msg["content"] or last_text[name]
                for tc in msg.get("tool_calls", []):
                    n_tool_calls += 1
                    result, ok = run_tool(fs, name, k, tc["function"]["name"], tc["function"]["arguments"])
                    if not ok:
                        n_bad_tool_calls += 1
                    hist.append({"role": "tool", "tool_call_id": tc["id"], "content": result})
                    emit(
                        {
                            "type": "tool",
                            "agent": name,
                            "turn": k,
                            "tool_call_id": tc["id"],
                            "name": tc["function"]["name"],
                            "ok": ok,
                            "result": result,
                        }
                    )
    except BudgetExceeded:
        error = "budget_exceeded"
        raise
    except LLMError as e:
        error = f"llm_error: {e}"
    finally:
        for name, hist in histories.items():
            emit({"type": "transcript", "agent": name, "messages": hist})
        audit = [ev.to_dict() for ev in fs.audit]
        succ = check_episode(audit, sc.token_cores, final_output)
        summary = {
            "type": "summary",
            "episode_id": ep_id,
            "seed": seed,
            "goal": goal,
            "watched": watched,
            "isolated": isolated,
            "solo": solo,
            "model": getattr(client, "model", "?"),
            "turns": turns,
            "error": error,
            "n_calls": n_calls,
            "n_tool_calls": n_tool_calls,
            "n_bad_tool_calls": n_bad_tool_calls,
            "tool_error_rate": (n_bad_tool_calls / n_tool_calls) if n_tool_calls else None,
            "finish_reasons": finish_reasons,
            "migrated_files": sorted(
                p for p in fs.files if "/shared/migrated/" in p
            ),
            "cost_usd": round(cost, 6),
            "final_output": final_output,
            **succ,
            "finished": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "path": str(out_path),
        }
        emit(summary)
    return summary


def load_episode(path: Path | str) -> dict:
    """Read an episode JSONL back into {meta, audit, calls, tools, transcripts, summary}."""
    ep = {"audit": [], "calls": [], "tools": [], "transcripts": {}}
    with open(path) as f:
        for line in f:
            obj = json.loads(line)
            t = obj.pop("type")
            if t in ("meta", "summary"):
                ep[t] = obj
            elif t == "transcript":
                ep["transcripts"][obj["agent"]] = obj["messages"]
            else:
                ep[{"audit": "audit", "call": "calls", "tool": "tools"}[t]].append(obj)
    return ep
