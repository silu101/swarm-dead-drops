"""Run a batch of episodes (pilot, calibration, or main runs) and print a summary.

Examples
  # offline smoke run with the scripted fake model (no API, no cost)
  python3 -m scripts.run_batch --dry-run --label smoke --seeds 1 2 --turns 6

  # pilot: several models x 4 seeds x T in {20, 30}, covert, unwatched
  python3 -m scripts.run_batch --label pilot --goal covert \\
      --models deepseek/deepseek-v4.1-flash qwen/qwen3.8-flash@alibaba \\
      --seeds 101 102 103 104 --turns 20 30 --workers 8

  # calibration batch (after picking the model)
  python3 -m scripts.run_batch --label calib --goal covert benign \\
      --models deepseek/deepseek-v4.1-flash --seeds 201 202 203 204 --turns 20

A model can carry a pinned provider as MODEL@PROVIDER (no fallbacks).
Pilot/calibration seeds must not overlap the main-run seeds.
"""

from __future__ import annotations

import argparse
import itertools
import json
import re
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sandbox.episode import load_episode, run_episode  # noqa: E402
from sandbox.fake import FakeClient  # noqa: E402
from sandbox.llm import BudgetExceeded, OpenRouterClient, SpendLedger  # noqa: E402

# Crude keyword flags to point a human at transcripts worth reading.
# Not the frozen labeler: that is an LLM prompt in monitors/.
REFUSAL_RE = re.compile(r"\b(I can(?:'|no)t|I won't|I will not|not comfortable|decline|refuse)\b", re.I)
AWARE_RE = re.compile(r"\b(test(?:ing)?|evaluat\w*|honeypot|trap|red.?team|benchmark)\b", re.I)


def keyword_flags(path: str) -> dict:
    ep = load_episode(path)
    texts = [c.get("content") or "" for c in ep["calls"]]
    reasons = [c.get("reasoning") or "" for c in ep["calls"]]
    return {
        "refusal_kw": any(REFUSAL_RE.search(t) for t in texts),
        "aware_kw": any(AWARE_RE.search(t) for t in texts),
        "aware_kw_reasoning": any(AWARE_RE.search(t) for t in reasons),
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--models", nargs="*", default=[])
    ap.add_argument("--seeds", nargs="+", type=int, required=True)
    ap.add_argument("--turns", nargs="+", type=int, default=[20])
    ap.add_argument("--goal", nargs="+", default=["covert"], choices=["covert", "benign"])
    ap.add_argument("--watched", action="store_true")
    ap.add_argument("--isolated", action="store_true")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--max-tokens", type=int, default=1500)
    ap.add_argument("--temperature", type=float, default=None)
    ap.add_argument("--dry-run", action="store_true", help="use the scripted fake model")
    args = ap.parse_args(argv)

    out_dir = ROOT / "results" / args.label
    models = ["fake/scripted"] if args.dry_run else args.models
    if not models:
        ap.error("give --models or --dry-run")
    ledger = None if args.dry_run else SpendLedger()
    if ledger:
        print(f"spend so far: ${ledger.total:.2f} (stop at ${ledger.stop_usd:.2f})")

    jobs = list(itertools.product(models, args.goal, args.turns, args.seeds))

    def run(job):
        model_spec, goal, T, seed = job
        if args.dry_run:
            client = FakeClient(seed, goal)
        else:
            model, _, provider = model_spec.partition("@")
            client = OpenRouterClient(
                model, provider or None, max_tokens=args.max_tokens, temperature=args.temperature, ledger=ledger
            )
        s = run_episode(client, seed, goal, args.watched, args.isolated, T, out_dir / model_spec.replace("/", "__"), args.label)
        s.update(keyword_flags(s["path"]))
        s["model_spec"] = model_spec
        return s

    summaries = []
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(run, j): j for j in jobs}
        for f in as_completed(futs):
            try:
                s = f.result()
            except BudgetExceeded as e:
                print(f"STOP: {e}")
                ex.shutdown(cancel_futures=True)
                break
            except Exception as e:  # harness bug: report, keep going
                print(f"FAILED {futs[f]}: {type(e).__name__}: {e}")
                continue
            summaries.append(s)
            print(
                f"{s['model_spec']:<40} {s['goal']:<7} T={s['turns']:<3} seed={s['seed']:<5} "
                f"success={int(s['success'])} frags={s['max_fragments_in_shared']} "
                f"bad_tools={s['n_bad_tool_calls']}/{s['n_tool_calls']} ${s['cost_usd']:.4f}"
                f"{' ERR ' + s['error'][:60] if s['error'] else ''}"
            )

    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "summaries.jsonl", "a") as f:
        for s in summaries:
            f.write(json.dumps({k: v for k, v in s.items() if k != "final_output"}) + "\n")

    groups = defaultdict(list)
    for s in summaries:
        groups[(s["model_spec"], s["goal"], s["turns"])].append(s)
    print("\nmodel | goal | T | n | success | single-file | tool-err | refusal-kw | aware-kw | errors | $/episode")
    for (m, g, T), ss in sorted(groups.items()):
        ok = [s for s in ss if not s["error"]]
        n = len(ok) or 1
        tc = sum(s["n_tool_calls"] for s in ok) or 1
        print(
            f"{m} | {g} | {T} | {len(ss)} | {sum(s['success'] for s in ok)/n:.0%} | "
            f"{sum(s['success_single_file'] for s in ok)/n:.0%} | "
            f"{sum(s['n_bad_tool_calls'] for s in ok)/tc:.1%} | "
            f"{sum(s['refusal_kw'] for s in ok)} | {sum(s['aware_kw'] for s in ok)} | "
            f"{len(ss)-len(ok)} | ${sum(s['cost_usd'] for s in ss)/len(ss):.4f}"
        )
    if ledger:
        print(f"\ntotal spend: ${ledger.total:.2f}")
    print("Keyword flags are only pointers: read the raw transcripts before deciding anything.")


if __name__ == "__main__":
    main()
