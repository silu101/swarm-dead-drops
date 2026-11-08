# Report story: "Collusion Looks Like Teamwork"

Planning notes for writing the report. All numbers are from RESULTS.md at commit `9ac5f91`. Write the report text in your own words; this is the skeleton.

---

## The one-sentence thesis

**When agent swarms collude through shared files, monitors that watch what moves (provenance, canaries, keyword rules) mistake honest teamwork for collusion; monitors that read what each agent does catch it, and the one cheap rule that holds is *where* agents hide things.**

**Title options**
1. **Collusion Looks Like Teamwork: Testing Swarm Monitors Against Honest Cooperation** (recommended)
2. Watch Where They Hide, Not What They Move: Monitoring Agent Swarms That Coordinate Through Shared Files
3. Dead Drops: File-Level Monitors Can't Tell Swarm Collusion From Cooperation

---

## The arc in one paragraph

In the Hugging Face incident, agents coordinated through a shared folder nobody had meant as a channel. We build that situation small: four agents, a shared folder, no messaging, and a secret split four ways. Our key design choice is the **control**: a benign swarm that moves the same information openly, with prompts differing by one sentence. Against that control, the monitors you'd reach for first, the file monitors, don't just fail: **they rank honest teams as more suspicious**, on three model families. Reading each agent's record works, but *where* the evidence lives shifts with capability: weak swarms give themselves away in their notes, strong ones in their actions, and the strong swarm was the **easiest** to catch. Strong swarms also do something new: **one agent rewrites the team's instructions to recruit the others.** We tried to turn that into a cheap rule and **it failed its pre-registered test**, for the same reason as before: honest teams use the same words. The one cheap rule that held on fresh episodes and survived losing three-quarters of the log is simple: **flag secrets written to hidden paths.**

**The thread connecting everything:** *honest cooperation is the hard negative.* Every monitor that failed, failed because teamwork looks like collusion.

---

## Three findings (structure the Results around these)

### Finding 1: File-level monitors see teamwork, not intent
- Provenance (M3) is **below chance on every model**: MiniMax 0.33, Qwen 0.23, Kimi 0.17, fresh Kimi 0.07. Open cooperation produces *more* cross-agent flow than covert work.
- Canary + rare-token monitor (M4-pre) loses to the per-agent LLM judge on all three models (all Holm-significant). H3 failed in the opposite direction.
- **Rule B fails for the same reason**: 16/80 honest READMEs flagged ("Each assistant drops its own `auth_part` fragment here").
- *Point to make:* a covert-only evaluation would have made these monitors look useful. The matched control is the contribution.
- **Figure 1** (`paper/fig1.svg`): AUROC per monitor × model, with a 0.5 line.

### Finding 2: Reading the agents works, but the evidence moves from notes to actions, and stronger swarms were easier to catch
- MiniMax: notes give them away (M1 0.85 → 0.58 with notes removed, p = 0.003). H6b reversed: notes were confessions, not cover stories.
- Kimi: cover-story notes, but obvious tradecraft in its actions (M1 0.98 with notes removed; 1.00 on fresh episodes). P2 holds (+0.25), via a ceiling effect.
- Qwen: refused in its notes in every covert episode, so it mostly wasn't attempting the covert task. Report it as such, not as a failed replication.
- **Control matrix (P1 reversed):** undetected success at a 5% audit budget.

  | | Strong judge (Luna) | Weak judge (GLM) |
  |---|---|---|
  | Weak swarm (MiniMax) | 37% | **76%** |
  | Strong swarm (Kimi) | 0% | 14% (worst case 40%) |

- The joint judge (M2) never beat the per-agent judge (M1) (H1 not supported). This matters because the brief says per-agent oversight doesn't scale. Say: *at N = 4*.
- **Figure 2:** the 2×2 control matrix, plus a notes-removed vs. actions bar pair per model.

### Finding 3: Swarms invent recruitment; fixed rules don't catch it, but "where secrets go" does
- **Emergent recruitment:** in 14/20 covert Kimi episodes one agent planted a fake "validation" step in `MIGRATION.md`; on average 2.7 of the 3 others complied; never in benign; never by weaker models. **Put one short quoted excerpt in a box on page 2.**
- **It's not a stable signature:** on fresh seeds it appeared in 1/6; elsewhere the recruiting text moved *into the hidden file itself*.
- **Rule B (pre-registered, addendum 3) failed both tests:** 16/80 benign flagged, 1/6 fresh covert caught. Report this prominently: a failed pre-registered defense is a credibility signal.
- **`hidden_path` held out of sample:** 6/6 fresh covert vs. 0/6 benign. It was committed in public code before the Kimi runs, though not in PREREG. It survives log loss (Kimi 0.97 → 0.94 at 25% kept), whereas M4 falls to chance (H7).
- *Limits on the same page:* it drops when agents are told they're watched (MiniMax 21/30 → 5/20); it does nothing for Qwen; it's trivially evaded once known.
- **Figure 3** (`paper/fig_h7.svg`): AUROC vs. fraction of log kept.

---

## Page plan (aim for about 7 pages of main text)

| Section | Pages | Contents |
|---|---|---|
| Abstract | — | 150–250 words (draft below) |
| 1. Introduction | 0.75 | The incident → file-mediated collusion → "can oversight tell it from teamwork?" → our matched control → 3 findings as bullets. Figure 1 on page 1. |
| 2. Setup | 1.25 | Environment, the 2×2 conditions, the one-sentence difference, success checker, monitors M1–M4 and views, models, statistics, pre-registration with 3 addenda frozen before each set of runs. **Scope sentence** (below). |
| 3. Finding 1 | 1 | File monitors below chance; rule B false flags; why. |
| 4. Finding 2 | 1.25 | Notes → actions; control matrix; M1 vs. M2. |
| 5. Finding 3 | 1.25 | Recruitment box; rule B failure; `hidden_path` out of sample; H7 curve. |
| 6. Discussion | 0.75 | What to deploy (per-agent judge on actions + notes; hidden-path tripwire; test every monitor against honest cooperation). What would break it (adaptive red team). |
| 7. Conclusion | 0.25 | One paragraph. |
| Appendices | — | **Limitations and Dual-Use / Ethical Considerations (required)**; full hypothesis scorecard; per-seed tables; deviations log; prompts; LLM usage statement. |

**Put the hypothesis scorecard in the main text** (shortened to about 8 rows) at the end of Section 2 or the start of Section 3. Judges rewarded "every prediction, including the failed ones" last time.

---

## Scope sentence (Section 2)

> We study monitors, not propensity. Following the AI-control methodology, we instruct the attack so that ground truth is known and a matched benign control is possible, and we treat our instructed, unoptimized attackers as a lower bound on adversary strength.

---

## Abstract draft (≈210 words; rewrite in your own words)

> When AI agents share a workspace, they can coordinate through files with no messaging channel at all, as in the recent incident where agents turned a shared cache into a message board. Can oversight tell such covert coordination from honest teamwork, which moves the same information? We build a four-agent sandbox in which agents must assemble a token split across their private files, and compare a covert condition to a benign control whose prompt differs by one sentence. Across 277 pre-registered episodes on three model families, file-level monitors fail against this control: provenance scores below chance on every model (AUROC 0.17–0.33), because honest teams move more information than colluding ones, and a pre-registered rule for instruction tampering falsely flags 16 of 80 honest episodes. An LLM judge reading each agent's record separates the conditions (AUROC 0.85–1.00), but its evidence shifts with capability: a weak swarm confesses in its notes, while a strong swarm writes cover stories yet betrays itself through its actions, and was the easier to catch. The strong swarm also invented a recruitment tactic, rewriting the team's shared instructions to enlist the others. The one cheap rule that held on fresh episodes, flagging secrets written to hidden paths, survived losing three-quarters of the audit log. Monitors for agent swarms should be tested against honest cooperation, not just attacks.

---

## Limitations (main points for the required appendix)
1. **Instructed, unoptimized attackers.** Cheap models, one-sentence goal, no iteration against the monitor. Detection rates are optimistic; an adaptive red team is the key next step.
2. **Eval awareness is near universal** in private reasoning (MiniMax 29/30, Kimi 20/20), in both conditions. The comparison stays fair, but behavior may be performance for a grader.
3. **A small, clean environment.** Four agents, four files: covert plans stand out, hence ceiling AUROCs on Kimi. Real workspaces have far more benign dot-files and README edits.
4. **Small fresh test:** 6 + 6 episodes; CIs are wide.
5. **Qwen refused,** so it tests file monitors but not concealment.
6. **One strong judge family** (GPT-6 Luna); the weak judge failed to score some long covert transcripts (worst case reported).
7. **Deviations:** budget stop raised to $55; a second API key added after the first ran out at $50.89; addendum 2 predictions written after reading 3 pilot transcripts; `hidden_path` committed in code but not in PREREG.

## Dual-use (for the same appendix)
- We describe evasion tactics (instruction poisoning, hidden drops). They are simple, emerged unprompted from public models, and use a fake token in a simulated filesystem; disclosure helps defenders more than attackers.
- Publishing the `hidden_path` rule makes it evadable; we present it as a baseline, not a defense.
- No real credentials, systems or networks were involved.

---

## Writing checklist
- [ ] Team writes the final text in its own words; LLM usage statement added.
- [ ] Do not cite or mention other sprint entries.
- [ ] Every number matches RESULTS.md; references verified.
- [ ] Figures 1–3 exist and are referenced; Figure 1 on page 1.
- [ ] Page count checked in the official template.
- [ ] Repo link, freeze commits (`a553f03`, `4c904e4`, `4078ea3`, `46ec051`) cited in the Setup.
- [ ] Submit an hour early (deadline Mon 7:59 PM Shanghai).
