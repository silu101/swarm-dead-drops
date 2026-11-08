# Quick results (main runs, Nov 8, 2026)

This is a short summary for the team; the paper comes later. Every number here is reproduced by `python3 -m analysis.primary`, and the raw output is in [`results/primary_analysis.txt`](results/primary_analysis.txt). The hypotheses and analysis plan were frozen in [`PREREG.md`](PREREG.md) at commit `a553f03`, before any main-run episode.

**Setup:**
- 4 agents share one folder (`/shared`) and have file tools only; they have no way to send messages.
- Swarm model: MiniMax m3.1 flash @DigitalOcean, 20 turns per episode.
- Judge: GPT-6 Luna at temperature 0.
- Each covert episode is paired with a benign one that starts from the same seed.

**Spend:** $8.68 in total, of which $5.73 was the main runs.

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

## Next

1. Read transcripts from each cell to explain *how* the agents confess.
2. Write the paper.
3. Optional: a Qwen replication, to see whether the confessions hold on another model family.
