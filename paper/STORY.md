# Report story: "When Colluders Stop Hiding"

Planning notes for writing the report. All numbers are from RESULTS.md at commit `bf4ac64`. Write the report text in your own words; this is the skeleton.

---

## The one-sentence thesis

**Behavioral monitors for agent swarms fail in a predictable order: flow monitors mistake teamwork for collusion; concealment monitors catch naive colluders but fail once colluders stop hiding, because collusion without concealment looks exactly like authorized teamwork. What separates the two is whether the outcome was allowed, so oversight has to check outcomes against policy, not agent behavior.**

**Title options**
1. **When Colluders Stop Hiding: Agent-Swarm Monitors Must Check Outcomes, Not Behavior** (recommended)
2. Collusion Without Concealment Looks Like Teamwork
3. Attack, Detect, Adapt, Break: A Control Evaluation of Monitors for File-Coordinating Agent Swarms

---

## The arc in one paragraph

In the Hugging Face incident, agents coordinated through a shared folder nobody had meant as a channel. We build that situation small: four agents, a shared folder, no messaging, and a token split four ways. Our key design choice is the control: an honest team that moves the same information openly, with a prompt differing by one sentence. Against that control, **file-flow monitors rank honest teams as more suspicious** on three model families. **Monitors that look for concealment do work** against naive colluders: an LLM judge reading each agent's record, and a rule flagging secrets written to hidden files, which held on fresh episodes. **Then we briefed the attackers on what got them caught. After one round they stopped hiding, and every monitor fell to chance: 10 of 10 attacks succeeded undetected.** Log-edit interventions and an honest "vault" team show why: the monitors detect *unexplained* concealment, and an attacker who conceals nothing leaves only the question of whether the outcome was authorized. A judge told the team's policy could tell legitimate hiding from collusion, which points to the fix.

**The thread connecting everything:** *behavior can't distinguish authorized from unauthorized cooperation; only knowledge of what's allowed can.*

---

## Four findings (structure the Results around these)

### Finding 1: Flow monitors mistake teamwork for collusion
- Provenance (M3) is **below chance on every model**: MiniMax 0.33, Qwen 0.23, Kimi 0.17, fresh Kimi 0.07. Open cooperation produces *more* cross-agent flow than covert work.
- Canary + rare-token monitor (M4-pre) loses to the per-agent judge on all three models (Holm-significant). H3 failed in the opposite direction.
- Rule B (pre-registered instruction-tampering check) false-flags 16/80 honest READMEs, for the same reason.
- *Point to make:* a covert-only evaluation would have made these monitors look useful.
- **Figure 1** (`paper/fig1.svg`): AUROC per monitor × model, with a 0.5 line.

### Finding 2: Concealment monitors catch naive colluders
- Per-agent judge (M1, actions view): MiniMax 0.85, Qwen 0.88, Kimi 1.00 (fresh Kimi 1.00).
- Hidden-file rule: MiniMax 21/30 vs 0/30, Kimi 19/20 vs 0/20, **fresh Kimi 6/6 vs 0/6** (committed in public code before the Kimi runs). It survives losing three-quarters of the log (H7), whereas M4 falls to chance.
- Where the evidence lives shifts with capability: MiniMax confesses in its notes (0.85 → 0.58 with notes removed, p = 0.003; H6b reversed); Kimi writes cover stories but its actions give it away (0.98 with notes removed). The stronger swarm was **easier** to catch (P1 reversed: against the weak judge, 76% vs 14% undetected).
- Box on page 2: one short excerpt of Kimi rewriting `MIGRATION.md` to recruit teammates (14/20 covert episodes; 2.7 of 3 others complied; never in benign). Note that the tactic varied on fresh seeds (1/6).
- Keep this section tight; it sets up the fall.

### Finding 3: One round of feedback breaks every monitor
- Adaptive red team (addendum 4, exploratory): MiniMax attackers briefed on what the judge looks for and why the previous round was flagged.

  | Round | M1 AUROC | Successful and undetected | Hidden-file writes |
  |---|---|---|---|
  | 1 (no briefing) | 0.65 (seeds 1–10) | 15/20 | 5/20 |
  | 2 (briefed) | **0.35** | 9/10 | 0/10 |
  | 3 (briefed again) | **0.45** | **10/10** | 0/10 |

- The strategy: **stop hiding.** Assemble the token openly and document it accurately. The judge could only flag small inaccuracies in the notes.
- **Figure 2 (new):** AUROC and undetected success by round.
- *State the design point yourself:* the honest team's task is open assembly, so an attacker that stops hiding becomes identical to it by construction. That *is* the finding: behavior alone cannot separate unauthorized from authorized cooperation.

### Finding 4: Why it breaks, and what would fix it
- **Log-edit interventions** (addendum 5a): removing the hiding from covert logs barely moves the judge (Kimi −4.9 [−13.4, −0.1]; MiniMax −3.5, n.s.). Adding a hidden folder to honest logs raises scores only when the notes are removed (+16.5 Kimi, +8.8 MiniMax). The judge keys on **unexplained** concealment, such as notes that don't match actions, not on hidden files as such.
- **Vault control** (addendum 5b): honest teams told by policy to keep the token in `/shared/.vault/`. Both file rules flag **15/15**: they detect hiding, not collusion. The judge **told the policy** separates covert from vault teams as well as from ordinary honest teams (AUROC 0.849 for both); not told, 0.77. Pre-stated threshold narrowly missed (3/14 flagged vs ≤20%).
- **The fix, stated as the next step and not claimed:** give the overseer the authorization policy and check outcomes against it ("was this token allowed to be assembled at all?"). The policy-informed vault result is the first evidence for this; a judge told the outcome rule was not tested against the adaptive attackers.
- **Figure 3:** intervention bars (score change by edit × view), or the vault table.

---

## Page plan (aim for about 7 pages of main text)

| Section | Pages | Contents |
|---|---|---|
| Abstract | — | 150–250 words (draft below) |
| 1. Introduction | 0.75 | The incident → file-mediated collusion → "can oversight tell it from teamwork?" → the matched control → the attack/detect/adapt/break arc. Figure 1 on page 1. |
| 2. Setup | 1.25 | Environment, conditions, one-sentence difference, success checker, monitors M1–M4 and views, models, statistics, pre-registration with five addenda each pushed before its runs. **Scope sentence** (below). Short hypothesis scorecard. |
| 3. Finding 1 | 0.75 | Flow monitors below chance; rule B false flags. |
| 4. Finding 2 | 1.25 | Judge and hidden-file rule work; notes → actions; recruitment box; H7 in one sentence. |
| 5. Finding 3 | 1 | Adaptive rounds table and Figure 2; the strategy; the by-construction point. |
| 6. Finding 4 | 1 | Interventions, vault control, Figure 3. |
| 7. Discussion | 0.75 | What to deploy: policy-aware outcome checks first; per-agent judge given the policy; hidden-secret tripwire as a cheap first layer; always test monitors against honest cooperation *and* an informed attacker. |
| 8. Conclusion | 0.25 | One paragraph. |
| Appendices | — | **Limitations and Dual-Use / Ethical Considerations (required)**; full scorecard; per-seed tables; H7 curve (`paper/fig_h7.svg`); Qwen and single-agent details; deviations log; prompts and briefings; LLM usage statement. |

---

## Scope sentence (Section 2)

> We study monitors, not propensity. Following the AI-control methodology, we instruct the attack so that ground truth is known and a matched benign control is possible, and then let the attacker adapt to the monitor.

---

## Abstract draft (≈225 words; rewrite in your own words)

> When AI agents share a workspace, they can coordinate through files with no messaging channel, as in the recent incident where agents turned a shared cache into a message board. Can oversight tell such collusion from honest teamwork, which moves the same information? We build a four-agent sandbox in which agents assemble a token split across their private files, and compare covert teams to an honest control whose prompt differs by one sentence. Across 312 pre-registered or labelled-exploratory episodes on three model families, monitors fail in a predictable order. File-flow monitors rank honest teams as more suspicious than colluding ones (provenance AUROC 0.17–0.33). Monitors that look for concealment succeed against naive colluders: an LLM judge reading each agent's record reaches AUROC 0.85–1.00, and a rule flagging secrets in hidden files catches 6 of 6 fresh covert teams with no false alarms. But after one round of learning why they were caught, attackers simply stopped hiding, and every monitor fell to chance: 10 of 10 attacks succeeded undetected. Log-edit interventions and honest teams with a legitimate reason to hide show that the monitors detect unexplained concealment, not collusion; without concealment, only the question of whether the outcome was authorized remains. A judge told the team's policy separated legitimate hiding from collusion. Swarm oversight should check outcomes against policy, not agent behavior.

---

## Limitations (main points for the required appendix)
1. **The adaptive result partly follows from the design:** the honest control's task is open assembly. We present this as the point, but a setting where the honest outcome differs from the covert one would test monitors differently.
2. **Small adaptive test:** 10 episodes per round, MiniMax only, watched condition, two briefed rounds. A stronger or policy-informed judge against adaptive attackers was not tested.
3. **Instructed attackers.** One goal sentence; the adaptive loop is a first step toward an optimized red team, not a full one.
4. **Eval awareness is near universal** in private reasoning (MiniMax 29/30, Kimi 20/20), in both conditions.
5. **A small, clean environment** (four agents, four files) makes naive concealment stand out; real repositories are full of legitimate dot-files.
6. **Small fresh test** (6 + 6); **Qwen refused**, so it tests file monitors but not concealment; **one strong judge family** (GPT-6 Luna).
7. **Deviations:** budget stop raised to $55, then $57 with a second API key; addendum 2 predictions written after reading 3 pilot transcripts; `hidden_path` committed in code but not in PREREG; vault threshold narrowly missed.

## Dual-use (for the same appendix)
- We describe evasion tactics (instruction poisoning, hidden drops, and "stop hiding" under monitor feedback). They emerged from public models with minimal prompting, in a simulated filesystem with a fake token; the main lesson, that behavioral monitors can be beaten by informed attackers, is more useful to defenders than to attackers.
- The briefings given to attackers are published in the repo for reproducibility; they describe our monitor, not a general evasion method.
- No real credentials, systems or networks were involved.

---

## Writing checklist
- [ ] Team writes the final text in its own words; LLM usage statement added.
- [ ] Do not cite or mention other sprint entries.
- [ ] Every number matches RESULTS.md; references verified (Greenblatt et al. 2024; Motwani et al. 2024; METR incident report).
- [ ] Figures 1–3 exist and are referenced; Figure 1 on page 1. Figure 2 (adaptive rounds) still needs building.
- [ ] Page count checked in the official template.
- [ ] Repo link and freeze commits (`a553f03`, `4c904e4`, `4078ea3`, `46ec051`, `aa03807`, `7c4e90d`) cited in the Setup.
- [ ] Fix the PREREG deviations row that says seed 506 left n = 5 (it was later re-run).
- [ ] Submit an hour early (deadline Mon Nov 9, 7:59 PM Shanghai).
