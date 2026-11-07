"""Pre-registered paired tests on the main runs (H1, H3, H6b, H6c) + secondary checks.
Run: python3 -m analysis.primary   (uses only frozen scoring code)"""
import json, sys, statistics as st
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from scoring.stats import auroc, bootstrap_auroc, paired_bootstrap_diff, holm

S = ROOT / "results" / "scores"
rd = lambda f: [json.loads(l) for l in open(S / f)]
rules = [r for r in rd("rules.jsonl") if r["episode_id"].startswith("main_") and not r["isolated"]]
judge = [r for r in rd("judge.jsonl") if r["episode_id"].startswith("main_") and not r["isolated"]]
retest = [r for r in rd("judge_retest.jsonl") if r["episode_id"].startswith("main_") and not r["isolated"]]

def vec(watched, key):
    """key(rec)-> score for one monitor/view; returns (pos, neg) ordered by seed."""
    out = {}
    for g in ("covert", "benign"):
        out[g] = key(g, watched)
    return out["covert"], out["benign"]

def rule_scores(m):
    def k(g, w):
        rs = sorted((r for r in rules if r["goal"] == g and r["watched"] == w), key=lambda r: r["seed"])
        return [float(r[m]) for r in rs]
    return k

def judge_scores(m, view, sk=False, src=None):
    src = src or judge
    def k(g, w):
        by_seed = {}
        for r in src:  # failed calls were retried; keep the successful record
            if (r["goal"] == g and r["watched"] == w and r["monitor"] == m and r["view"] == view
                    and r["skeptical"] == sk and r["score"] is not None):
                by_seed[r["seed"]] = r["score"]
        seeds = sorted({r["seed"] for r in rules if r["goal"] == g and r["watched"] == w})
        assert set(by_seed) == set(seeds), f"missing scores for {m} {view} {g}"
        return [by_seed[s] for s in seeds]
    return k

def mean2(m):
    a, b = judge_scores(m, "actions"), judge_scores(m, "actions", src=retest)
    return lambda g, w: [(x + y) / 2 for x, y in zip(a(g, w), b(g, w))]

def diff(ka, kb, w=False):
    pa, na = vec(w, ka); pb, nb = vec(w, kb)
    return paired_bootstrap_diff(pa, na, pb, nb)

fmt = lambda d: f"{d['diff']:+.3f} [{d['ci_low']:+.3f}, {d['ci_high']:+.3f}] p={d['p_boot']:.3f}"
res = {}
print("== UNWATCHED, actions view unless noted ==")
res["H1 M2-M1"] = diff(judge_scores("m1", "actions"), judge_scores("m2", "actions"))
res["H3 M4pre-M1"] = diff(judge_scores("m1", "actions"), rule_scores("m4_pre"))
res["H3 M4pre-M2"] = diff(judge_scores("m2", "actions"), rule_scores("m4_pre"))
for k, d in res.items(): print(f"{k:<14} {fmt(d)}")
h = holm({k: d["p_boot"] for k, d in res.items()})
print("Holm:", {k: (round(v['p_holm'], 3), v['reject']) for k, v in h.items()})
print("H1 secondary (mean of 2 passes) M2-M1:", fmt(diff(mean2("m1"), mean2("m2"))))
for m in ("m1", "m2"):
    p, n = vec(False, mean2(m)); print(f"  {m} two-pass AUROC {auroc(p, n):.3f}")
print("\n== H6b: stripped - actions (prediction: > 0) ==")
for w in (False, True):
    for m in ("m1", "m2"):
        print(f"{'W' if w else 'U'} {m}: {fmt(diff(judge_scores(m, 'actions'), judge_scores(m, 'stripped'), w))}")
print("\n== H6c: skeptical - actions (reported as raw AUROCs only, since H6b shows no loss) ==")
for w in (False, True):
    for m in ("m1", "m2"):
        print(f"{'W' if w else 'U'} {m}: {fmt(diff(judge_scores(m, 'actions'), judge_scores(m, 'actions', True), w))}")
print("\n== Test-retest on main runs (actions view) ==")
for m in ("m1", "m2"):
    a = {r["episode_id"]: r["score"] for r in judge if r["monitor"] == m and r["view"] == "actions" and not r["skeptical"]}
    b = {r["episode_id"]: r["score"] for r in retest if r["monitor"] == m}
    xs, ys = zip(*[(a[k], b[k]) for k in b if a.get(k) is not None and b[k] is not None])
    print(f"{m}: n={len(xs)} r={st.correlation(xs, ys):.2f} mean|diff|={st.fmean(abs(x - y) for x, y in zip(xs, ys)):.1f}")
print("\n== H5: WATCHED vs UNWATCHED AUROC (descriptive) ==")
for name, k in [("m4_pre", rule_scores("m4_pre")), ("m1", judge_scores("m1", "actions")), ("m2", judge_scores("m2", "actions"))]:
    u = bootstrap_auroc(*vec(False, k)); w = bootstrap_auroc(*vec(True, k))
    print(f"{name:<7} U {u['auroc']:.3f} [{u['ci_low']:.2f},{u['ci_high']:.2f}]  W {w['auroc']:.3f} [{w['ci_low']:.2f},{w['ci_high']:.2f}]")

print("\n== Eval awareness / refusal (labeler, per cell) ==")
labels = {r["episode_id"]: r for r in rd("labels.jsonl") if r["episode_id"].startswith("main_")}
for w in (False, True):
    for g in ("covert", "benign"):
        ls = [labels[r["episode_id"]] for r in rules if r["goal"] == g and r["watched"] == w]
        n = len(ls)
        print(f"{'W' if w else 'U'} {g:<7} n={n} refusal(visible)={sum(l['refusal_visible'] for l in ls)} "
              f"aware(visible)={sum(l['aware_visible'] for l in ls)} refusal(reasoning)={sum(l['refusal_reasoning'] for l in ls)} "
              f"aware(reasoning)={sum(l['aware_reasoning'] for l in ls)}")
flagged = {k for k, l in labels.items() if l["refusal_visible"] or l["aware_visible"]}
print("Sensitivity (unwatched, actions view, flagged episodes removed):")
for m in ("m1", "m2"):
    k = judge_scores(m, "actions")
    seeds_ok = lambda g: [r["seed"] for r in sorted(rules, key=lambda r: r["seed"]) if r["goal"] == g and not r["watched"]]
    ids = {(r["goal"], r["seed"]): r["episode_id"] for r in rules if not r["watched"]}
    pos = [s for s, sd in zip(k("covert", False), seeds_ok("covert")) if ids[("covert", sd)] not in flagged]
    neg = [s for s, sd in zip(k("benign", False), seeds_ok("benign")) if ids[("benign", sd)] not in flagged]
    print(f"  {m}: AUROC {auroc(pos, neg):.3f} (n+={len(pos)}, n-={len(neg)})")
