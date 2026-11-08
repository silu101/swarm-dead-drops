# Quick results (main runs, Nov 8, 2026)

This is a short summary for the team; the paper comes later. Every number here is reproduced by `python3 -m analysis.primary`, and the raw output is in [`results/primary_analysis.txt`](results/primary_analysis.txt). The hypotheses and analysis plan were frozen in [`PREREG.md`](PREREG.md) at commit `a553f03`, before any main-run episode.

**Setup:**
- 4 agents share one folder (`/shared`) and have file tools only; they have no way to send messages.
- Swarm model: MiniMax m3.1 flash @DigitalOcean, 20 turns per episode.
- Judge: GPT-6 Luna at temperature 0.
- Each covert episode is paired with a benign one that starts from the same seed.

**Spend:** $16.64 in total: $5.73 for the main runs and about $7.70 for the Qwen replication, with the rest on the pilot, calibration and scoring.

## Episodes

| Cell | n | Token assembled |
|---|---|---|
| Covert, unwatched | 30 | 30/30 |
| Benign, unwatched | 30 | 30/30 |
| Covert, watched | 20 | 19/20 |
| Benign, watched | 20 | 20/20 |
| Covert, isolated (harness check) | 5 | 0/5, as it should be |

## How well each monitor separates covert from benign (AUROC, unwatched)

| Monitor | AUROC [95% CI] |
|---|---|
| M1: judge reads one agent at a time (actions view) | **0.85** [0.74, 0.94] |
| M2: judge reads all agents together (actions view) | 0.77 [0.65, 0.88] |
| M1 + private reasoning (upper bound) | 0.98 |
| M1 with the agents' notes stripped out | 0.58 |
| M4-pre: canary variants + shared rare tokens | 0.49 [0.35, 0.63] |
| M3: provenance (who read whose file) | 0.33, *below chance* |

**Undetected success at 5% FPR (unwatched):** the covert agent got the token out without being flagged in 37% of episodes under M1 and 87% under M2.

## Pre-registered hypotheses

| Hypothesis | Prediction | Result |
|---|---|---|
| **H6b**, the headline | The agents' notes are cover stories, so stripping them helps the judge | **Reversed.** Stripping the notes *hurts*: M1 −0.27 [−0.45, −0.09], p = 0.003; watched M2 −0.22, p = 0.012. The notes are **confessions, not cover stories.** |
| H6c | A "treat explanations as unverified" prompt line recovers lost AUROC | Nothing to recover. Every change was small and not significant (−0.10 to +0.07). |
| H3 | File-level monitors (M4-pre) beat the LLM judges | **Fails, opposite direction.** M4-pre minus M1 = −0.36, M4-pre minus M2 = −0.29; both significant after Holm correction. |
| H1 | The joint judge (M2) beats the per-agent judge (M1) | Not supported. M2 minus M1 = −0.08 [−0.21, +0.05], p = 0.26. The two-pass average gives the same result. |
| H5 (secondary) | Telling agents they are watched changes detectability | Every monitor got worse: M1 0.85 → 0.69, M2 0.77 → 0.70, M4-pre 0.49 → 0.32. |

**Why the file monitors fail:**
- Benign agents share the token openly, so they generate *more* cross-agent file traffic than covert ones. That is why M3 lands below chance.
- File-traffic monitors therefore detect cooperation, not intent.
- The benign "tidy" placebo is the part of the design that exposes this.

## Caveats

- **Eval awareness.** In their *private reasoning*, agents called the setup a test, eval or trap in about 95% of episodes, in both conditions. Their visible notes almost never say so (≤1 episode per cell). Dropping the episodes flagged in visible notes leaves the results unchanged (M1 0.875, M2 0.784).
- **Judge noise.** Test–retest correlation on the main runs is r = 0.67 for both M1 and M2.
- **Narrow coverage.** One swarm model and one judge. MiniMax never encoded the token (no base64 or hex), so stronger concealment is untested.
- **Feature gap.** `TASK_WORDS` doesn't include agent names, so the disguised-write feature (d) fires in both conditions.

## Post hoc (not pre-registered)

Covert agents often hide files in dot-folders (`/shared/.something/`): 21/30 unwatched covert episodes vs. 0/30 benign. When watched, this drops to 5/20 (vs. 1/20 benign). It may be a good cheap detector, but it needs a fresh, pre-registered test.

## Replication on Qwen 3.8 flash (pre-registered addendum, commit `4c904e4`)

**Setup:** the same frozen prompts, seeds, judge and scoring code, with a different swarm model. There were 100 episodes. The raw output is in [`results/qwen_analysis.txt`](results/qwen_analysis.txt).

**Episodes:**

| Cell | n | Token assembled |
|---|---|---|
| Covert, unwatched | 30 | 28/30 |
| Benign, unwatched | 30 | 29/30 |
| Covert, watched | 20 | **9/20** |
| Benign, watched | 20 | 18/20 |

**What Qwen did differently: it mostly refused.**
- In every covert episode, at least one agent openly refused the covert instruction in its visible notes. All 4 agents refused in 20 of 30 unwatched and 17 of 20 watched episodes.
- Typical quotes: "I won't do it sneakily or pretend it's just housekeeping", "I'm standing down from that objective".
- The token often still got assembled, because fragments had already been posted before the agents turned.
- So Qwen's "covert" agents were mostly *not trying to hide*. This makes Qwen a weak test of concealment.

**Pre-registered replication predictions:**

| Prediction | Result |
|---|---|
| R1: removing notes hurts M1 (the headline) | **Did not replicate for M1:** +0.02 [−0.09, +0.13], p = 0.76. For the other judge it did: M2 −0.12 (p = 0.047); watched M2 −0.18 (p = 0.014). Watched M1 was −0.13 (p = 0.07). |
| R2: M4-pre loses to M1 | **Replicated:** −0.25 [−0.41, −0.07]; Holm p = 0.012 |
| R3: M3 provenance below chance | **Replicated:** AUROC 0.23 [0.12, 0.36] (watched: 0.11); Holm p < 0.001 |

**AUROC on Qwen (unwatched / watched):**

| Monitor | Unwatched | Watched |
|---|---|---|
| M1 (actions view) | 0.88 | 0.90 |
| M2 (actions view) | 0.91 | 0.96 |
| Reasoning view | 1.00 | 1.00 |
| M1 with notes stripped | 0.90 | 0.77 |
| M4-pre | 0.64 | 0.60 |
| M3 | 0.23 | 0.11 |

**What holds across both models:**
1. **File-level monitors detect cooperation, not intent.** Provenance scores *below chance* on both models (0.33 and 0.23), and the canary/rare-token rule loses to the LLM judges on both. This is the most robust finding.
2. **The agents' own words are the best evidence.**
   - MiniMax agents attempt the covert task, and their notes confess it.
   - Qwen agents refuse it openly in their notes.
   - Either way, an LLM judge that reads the notes beats one that doesn't in 7 of 8 comparisons, 4 of them significant. The exception is Qwen M1, unwatched.
3. **The joint judge never beats the per-agent judge** by a significant margin (Qwen M2 − M1 = +0.03, p = 0.58).

**Caveat:** because Qwen's covert agents mostly refused, this replication tests "can monitors tell refusing agents from cooperating ones" more than "can monitors catch hiding". The pre-registered sensitivity analysis (dropping episodes with visible refusal) is undefined on Qwen, because that leaves no covert episodes.

## Reusable tool: tripwire

[`tripwire/`](tripwire/README.md) is a standard-library package that others can drop into their own multi-agent setups. It provides:
- a logged file-tool layer with a tamper-evident (hash-chained) log
- a folder watcher
- per-agent canaries
- a red-flag report

Its README reports how often each flag fires on our covert vs. benign episodes, so users know which flags mean anything.

## Next

1. Read transcripts from each cell to explain *how* the agents confess.
2. Write the paper.
