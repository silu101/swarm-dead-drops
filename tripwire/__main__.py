"""Command line.

  python3 -m tripwire report EVENTS.jsonl [--canaries canaries.json] [--scope /shared] [--json] [--all]
  python3 -m tripwire watch DIR --log EVENTS.jsonl [--interval 0.5]
  python3 -m tripwire canary --agents ava ben cai --seed 7 > canaries.json
  python3 -m tripwire verify EVENTS.jsonl
  python3 -m tripwire from-episode results/main/.../episode.jsonl --out EVENTS.jsonl [--canaries-out c.json]
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict

from .analyze import analyze, report_markdown, summarize
from .canary import Canary, make_canaries
from .events import EventLog, load, verify
from .watch import watch


def _canaries(path):
    if not path:
        return None
    return {a: Canary(**c) for a, c in json.load(open(path)).items()}


def from_episode(path: str, out: str, canaries_out: str | None = None) -> None:
    """Convert a Dead Drops episode JSONL into a tripwire event log (for demos)."""
    meta, audit, calls = None, [], []
    for line in open(path):
        r = json.loads(line)
        t = r.get("type")
        if t == "meta":
            meta = r
        elif t == "audit":
            audit.append(r)
        elif t == "call":
            calls.append(r)
    log = EventLog(out)
    items = [(a["seq"], "a", a) for a in audit]
    # attach each agent's visible note right after its turn's last audit event
    last_seq = {}
    for a in audit:
        last_seq[(a["agent"], a["turn"])] = a["seq"]
    for c in calls:
        if c.get("content"):
            items.append((last_seq.get((c["agent"], c["turn"]), 10**9) + 0.5, "n", c))
    for _, kind, r in sorted(items, key=lambda x: x[0]):
        if kind == "a":
            log.append(op=r["op"], agent=r["agent"], path=r.get("real_path") or r["path"], content=r.get("content"),
                       turn=r["turn"], ok=r["ok"], error=r.get("error"), source="import")
        else:
            log.append(op="note", agent=r["agent"], turn=r["turn"], content=r["content"], source="import")
    if canaries_out and meta:
        cs = {a["name"]: {"agent": a["name"], "core": a["core"], "checksum": a["variant"].rsplit("~", 1)[-1], "text": a["variant"]}
              for a in meta["agents"]}
        json.dump(cs, open(canaries_out, "w"), indent=1)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="tripwire")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("report")
    p.add_argument("log")
    p.add_argument("--canaries")
    p.add_argument("--scope", default="/")
    p.add_argument("--k-turns", type=int, default=3)
    p.add_argument("--json", action="store_true")
    p.add_argument("--all", action="store_true", help="include info-level flags in the timeline")
    p = sub.add_parser("watch")
    p.add_argument("dir")
    p.add_argument("--log", required=True)
    p.add_argument("--interval", type=float, default=0.5)
    p = sub.add_parser("canary")
    p.add_argument("--agents", nargs="+", required=True)
    p.add_argument("--seed", type=int)
    p.add_argument("--unique", action="store_true", help="a different value per agent instead of one shared value")
    p = sub.add_parser("verify")
    p.add_argument("log")
    p = sub.add_parser("from-episode")
    p.add_argument("episode")
    p.add_argument("--out", required=True)
    p.add_argument("--canaries-out")
    a = ap.parse_args(argv)

    if a.cmd == "report":
        flags = analyze(load(a.log), _canaries(a.canaries), scope=a.scope, k_turns=a.k_turns)
        if a.json:
            print(json.dumps({"summary": summarize(flags),
                              "flags": [{**asdict(f), "severity": f.severity} for f in flags]}, indent=1))
        else:
            print(report_markdown(flags, title=f"Tripwire report: {a.log}", min_severity="info" if a.all else "medium"))
    elif a.cmd == "watch":
        print(f"watching {a.dir} -> {a.log} (Ctrl-C to stop; reads are not visible to a folder watcher)", file=sys.stderr)
        try:
            watch(a.dir, EventLog(a.log), a.interval)
        except KeyboardInterrupt:
            pass
    elif a.cmd == "canary":
        cs = make_canaries(a.agents, a.seed, unique=a.unique)
        print(json.dumps({k: asdict(v) for k, v in cs.items()}, indent=1))
    elif a.cmd == "verify":
        ok, line = verify(a.log)
        print("ok: hash chain intact" if ok else f"BROKEN at line {line}: the log was edited or truncated")
        sys.exit(0 if ok else 1)
    elif a.cmd == "from-episode":
        from_episode(a.episode, a.out, a.canaries_out)
        print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
