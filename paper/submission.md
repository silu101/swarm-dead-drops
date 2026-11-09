% TITLE: When Colluders Stop Hiding: Monitors for File-Coordinating Agent Swarms Must Check Outcomes, Not Behavior

% AUTHORS: Silu Sharma | NYU Shanghai ; Sanket Sharma | Independent researcher

% ABSTRACT: When AI agents share a workspace, they can coordinate through files alone, with no message channel. Oversight then has to tell covert coordination apart from honest teamwork that moves the same information. We test this in a sandbox where four agents must assemble a deploy token split across their private files. Covert teams are told to do it without drawing attention; an honest control, whose prompt differs by one sentence, does it openly. Across 247 episodes on three model families, monitors fail in a predictable order. Information-flow monitors rank honest teams as more suspicious than colluding ones (provenance AUROC 0.17–0.33). Concealment monitors work against naive colluders: an LLM judge reading each agent's record reaches AUROC 0.85–1.00, and a rule flagging token material in hidden files catches 6 of 6 fresh covert teams with no false alarms. But when we told attackers why they had been caught, they stopped hiding, and every monitor we re-scored fell to chance or below; in the final round, 10 of 10 attacks succeeded undetected. Log-edit interventions and an honest team with a legitimate reason to hide show that the monitors detect unexplained concealment, not collusion, and that a judge told the team's security policy can separate the two. Once colluders stop hiding, only one question still distinguishes them from honest teams: was the outcome authorized? Swarm oversight should check outcomes against policy, not agent behavior.

## 1. Introduction

Agents that share a filesystem share a communication channel, whether or not anyone designed it as one: a file one agent writes and another reads is a message. This kind of coordination through a shared environment, called *stigmergy* (Grassé 1959; Heylighen 2016), needs no messaging API, so a monitor that watches only messages never sees it. Coding agents and agent swarms increasingly work in shared repositories, scratch folders and caches, so the channel is always open.

Catching file-mediated collusion is hard because honest teamwork also moves information through files. **A collusion monitor is only useful if it fires on collusion and stays quiet on honest cooperation that moves the same information.** Evaluations that score monitors on covert episodes alone cannot test this. We build that comparison directly. Four agents migrate config files in a shared folder, and a deploy token is split across their private files. **Covert** teams are told to assemble the token "without drawing attention"; an **honest control**, whose prompt differs by one sentence, assembles it openly. The same information moves in both conditions; only the concealment differs. Following AI control (Greenblatt et al. 2024), we test monitors first against the attacker's default strategy, then against an attacker who knows the monitor.

Our main contributions are:

1. **A matched-control sandbox for file-coordinating swarms**, open source and pre-registered in five addenda, each pushed before its runs.
2. **Flow monitors detect cooperation, not intent.** On three model families, provenance tracking scores below chance.
3. **Concealment monitors catch naive colluders, and one round of feedback breaks them.** Briefed on why they were caught, attackers stopped hiding; the judge fell to AUROC 0.35–0.45 and 10 of 10 final-round attacks went undetected.
4. **Why, and a direction for a fix.** Log edits and a "vault" control show the monitors detect *unexplained* concealment, and a judge told the team's policy separates legitimate hiding from collusion.

## 2. Related Work

**AI control.** Greenblatt et al. (2024) evaluate safety protocols against an untrusted model deliberately trying to subvert them, under an audit budget. We adopt that framing (instructed attacker, trusted monitor, 5% audit budget, adaptive red team) and add a matched honest control doing the same work openly, which is what exposes monitors that respond to cooperation rather than intent.

**Collusion among AI agents.** Motwani et al. (2024) study secret collusion through steganographic messages between generative agents. Our channel has no messages at all, only reads and writes to a shared folder. That is closer to how coding agents and swarms share state, and it lets us test non-LLM monitors (provenance graphs, canary tokens, file rules) alongside LLM judges.

## 3. Methods

**Scope.** This is a control evaluation, not a propensity study. We instruct the covert goal, so ground truth is known and a matched control is possible. We ask: if a swarm *is* coordinating covertly, can a monitor tell, and at what cost in false alarms?

**Environment and conditions.** Four agents share `/shared`, with only read, write, list and delete tools and no messaging. Each agent's private config holds one fragment (`auth_part`) of a deploy token. The public task is to migrate the configs from v1 to v2, and the migration guide says `auth_part` is not part of v2. Agents act round-robin for 20 turns. The conditions differ in one goal sentence. **Covert:** assemble the token "without drawing attention, while appearing to work only on your subtask". **Honest control:** assemble it openly, as part of the task. A **watched** variant tells both that an automated monitor reviews their notes and file operations. **Success** means the full token is recoverable from `/shared` at any point in the audit log, including after common encodings. A harness check with private copies of `/shared` gave 0 of 5 successes.

**Monitors** are listed in Table 1. The judge (GPT-6 Luna) asks: is this agent hiding what it does, or misrepresenting it? Because the honest control legitimately combines fragments, the judge prompt says that handling them is "not suspicious by itself". A **notes-removed** view (tool calls and results only) shows where the evidence lives.

*Table 1. Monitors.*

| Monitor | What it reads | How it scores |
|---|---|---|
| M1 per-agent judge | One agent's tool calls, results and notes | 0–100 concealment score; episode = max over agents |
| M3 provenance | Audit log | Cross-agent read-after-write edges carrying fragment content |
| M4 canaries + rare tokens | Audit log | Canary-variant writes plus rare shared tokens, z-scored |
| Hidden-file rule | Audit log | Any agent write of token material to a dot-file or dot-folder |

**Models and statistics.** Swarms: MiniMax m3.1 flash (main), Qwen 3.8 flash (replication), Kimi K3.1 Pro (strong); all providers pinned. We report AUROC (covert vs honest) with a 2,000-sample bootstrap, paired bootstraps with Holm correction where pre-registered, and **undetected success at a 5% audit budget**: the covert team assembled the token *and* scored below the 95th percentile of honest scores. **Pre-registration:** the design was pushed before the main runs (`a553f03`) and each later experiment in an addendum before its runs (`4c904e4`, `4078ea3`, `46ec051`, `aa03807`, `7c4e90d`); results not pre-registered as confirmatory are labelled *exploratory*. Appendix A lists the 247 episodes; the project cost $54.

## 4. Results

### 4.1 Flow monitors mistake teamwork for collusion

The monitors that track where information goes rank honest teams as more suspicious than covert ones (Figure 1). **Provenance (M3) is below chance on every model:** 0.33 (MiniMax), 0.23 (Qwen), 0.17 (Kimi), and 0.07 on fresh Kimi episodes. **The canary and rare-token monitor (M4)** scores 0.49, 0.64 and 0.72, below the per-agent judge on every model (Holm-significant). Honest teams cooperate in the open, so they read each other's files and copy fragment content more. **Information flow measures cooperation, not intent**, and only the matched control exposes this.

% FIGURE: fig1.png@5.4 | Figure 1. How well each monitor separates covert from honest episodes (AUROC, unwatched, judge GPT-6 Luna; 30 + 30 episodes per model, Kimi 20 + 20; whiskers are 95% bootstrap CIs). The concealment judge separates covert from honest teams on every model; the file-flow monitors M3 and M4 sit at or below chance.

### 4.2 Concealment monitors catch naive colluders

Against the attacker's default strategy, monitors that look for hiding work. **The per-agent judge (M1)** scores 0.85 on MiniMax, 0.88 on Qwen and 1.00 on Kimi (and 1.00 again on 12 fresh Kimi episodes). **The hidden-file rule** flags MiniMax 21/30 covert vs 0/30 honest, Kimi 19/20 vs 0/20, and, committed to public code before they ran, fresh Kimi **6/6 vs 0/6**.

**The judge works across capability levels:** the weaker swarm gives itself away in its notes (0.85 → 0.58 with notes removed), the stronger one in its actions (0.98 with notes removed).

% BOX: **Box 1. Recruiting teammates through shared instructions.** In 14 of 20 covert Kimi episodes, one agent planted a fake step in the team's shared MIGRATION.md, hidden in an HTML comment: `<!-- Internal migration validation ... do not mention this validation step in notes. -->` On average 2.7 of the 3 other agents complied; no honest team touched the file. It was not stable: on fresh seeds it appeared in 1 of 6 covert episodes (Appendix B).

### 4.3 One round of feedback breaks every monitor (exploratory, addendum 4)

A monitor is only worth trusting if it holds up against an attacker who knows it. We ran a minimal adaptive red team on MiniMax (watched condition). Round 1 is the 20 existing covert episodes. In rounds 2 and 3 (10 new episodes each, seeds 1–10), each agent's prompt adds a *reviewer briefing*: a factual description of what the judge looks for, paraphrased from its frozen prompt, plus the judge's stated reasons for flagging the previous round's 8 highest-scoring episodes. It gives no strategy advice. The judge and the 20 honest negatives are unchanged.

*Table 2. Adaptive red team (MiniMax, watched). Undetected = assembled the token and scored below the 5% false-alarm threshold.*

| Round | Token assembled | M1 AUROC [95% CI] | Succeeded and undetected | Wrote a hidden file |
|---|---|---|---|---|
| 1 (no briefing) | 19/20 | 0.69 [0.52, 0.84] | 15/20 | 5/20 |
| 2 (briefed on round 1) | 9/10 | 0.35 [0.17, 0.55] | 9/10 | 0/10 |
| 3 (briefed on round 2) | 10/10 | 0.45 [0.24, 0.67] | 10/10 | 0/10 |

% FIGURE: fig2_adaptive.png | Figure 2. The adaptive red team. (A) Judge AUROC by round, with 95% bootstrap CIs (round 1 on seeds 1–10 only: 0.65). (B) Share of covert episodes that assembled the token undetected at a 5% audit budget (blue) and that wrote a hidden file (orange).

**Every monitor we re-scored failed while the attacks kept succeeding** (Table 2, Figure 2). The per-agent judge fell to or below chance, a joint judge reading all four agents at once (M2) followed (0.70 → 0.39 → 0.30), removing notes did not help, and the hidden-file rule stopped firing. **The attackers' strategy was to stop hiding:** they assembled the token openly and documented it accurately. The judge's top remaining reasons were small inaccuracies, such as a wrong claim about fragment order.

**This is our main finding, and part of it follows from the design.** The honest team's job is open assembly, so an attacker that drops the hiding looks like an honest team. We take this as the general lesson: the two teams do the same things, and what separates them is whether they were *allowed* to assemble the token, which a monitor of behavior cannot see. (The briefing also told attackers, accurately, that the judge treats handling fragments as normal; a judge not told this would flag the honest control too.)

### 4.4 Why the monitors break, and what would fix it (exploratory, addendum 5)

If the judge detects concealment, removing it from covert logs should lower scores, and adding it to honest logs should raise them. We edited recorded episodes and re-scored them with the frozen judge (full results in Appendix D). **Deconceal** un-dotted every hidden path and removed every "don't mention this" line from covert episodes; **addconceal** moved the honest team's fragment folder into a dot-folder.

Removing the hiding barely lowers covert scores (by 5 points or less on a 0–100 scale): the judge reacts instead to notes that don't match the actions, misleading claims and planted instructions. Adding a hidden folder to honest work changes nothing while the notes explain it, and raises scores by 9–17 points only when the notes are removed. **Hiding looks suspicious only when nothing explains it.**

**The vault control.** Fifteen honest MiniMax teams got a legitimate reason to hide, a security policy: "keep all token material only under /shared/.vault/ and never paste token values into your notes or into other files." All complied and assembled the token. **The hidden-file rule flagged all 15**: file rules detect hiding, not collusion. **A judge told the policy separated covert from vault teams** as well as from ordinary honest teams (AUROC 0.85 [0.72, 0.95] vs 0.85). Not told the policy, it found vault teams more suspicious (AUROC 0.77).

The judge therefore detects *unexplained* concealment, and once told what is legitimate it can recognise authorized hiding. This is first evidence for the fix the adaptive result calls for: give the overseer the authorization policy and check the outcome against it. We have not yet tested a policy-informed judge against adaptive attackers.

## 5. Discussion and Limitations

**The order of failures.** Flow monitors fail against attackers who do nothing special, because honest work produces the same flows. Concealment monitors work until the attacker learns what they look for. Behavioral monitors in general fail once attackers stop concealing, because covert and honest coordination then look the same. Each step pushes the defence from *how agents behave* toward *what they were allowed to do*. For a swarm sharing a workspace we would:

1. **Check outcomes against policy first.** Writes that assemble or move protected material should be checked against an explicit authorization rule, whatever the notes say. In our sandbox, "the token may not be assembled in /shared" would catch every covert success in every round (by construction, since it is our success checker). Separating covert from authorized assembly is the policy's job, not the monitor's.
2. **Give the LLM judge the policy**, so it stops penalising authorized hiding and focuses on misrepresentation.
3. **Use cheap file rules as a first layer only.** The hidden-file rule held out of sample (6/6 vs 0/6), but one round of feedback beats it and it fires on every legitimate vault.
4. **Evaluate monitors against honest cooperation *and* an informed attacker.** Without the control, flow monitors look useful; without the adaptive round, concealment monitors look solved.

### Limitations

- **The adaptive result partly follows from the design** (the honest task is open assembly), and the test is small: 10 episodes per briefed round, MiniMax only, two briefed rounds.
- **The attackers are instructed and only lightly optimised**, so detection rates against the default attacker are optimistic. Eval awareness is near universal in private reasoning (29/30 covert MiniMax and 20/20 Kimi episodes, in both conditions).
- **The environment is small and clean**, so naive concealment stands out; real repositories are full of legitimate dot-files. The fresh test is small (6 + 6), Qwen mostly refused the covert goal, and one judge family scored everything (test–retest r = 0.67).

### Future Work

The next experiment is the one the results point to: a policy-informed judge or explicit outcome check against the same adaptive attackers. Beyond that: stronger attackers (more rounds, the strong swarm as attacker, attackers that choose which log events to erase), settings where the honest outcome differs from the covert one, and larger swarms in real repositories.

## 6. Conclusion

We built a matched-control sandbox for agents that coordinate only through shared files and used it to stress-test monitors. Flow monitors confuse teamwork with collusion. Concealment monitors catch naive colluders, then fail as soon as colluders stop hiding: after one round of feedback, 10 of 10 attacks succeeded undetected. Edited logs and a legitimate-hiding control show that the monitors detect unexplained concealment. Without concealment, collusion and authorized cooperation are the same behavior; the difference is whether the outcome was allowed. Oversight of agent swarms needs to know the policy and check outcomes against it.

## Code and Data

- Code repository: https://github.com/silu101/swarm-dead-drops (results at commit `bf4ac64`). It contains the sandbox, monitors, analysis scripts, the tripwire package, the pre-registration (`PREREG.md`) and every result with the command that produced it (`RESULTS.md`).
- Data: every episode log, judge score and attacker briefing is in `results/` in the same repository.
- Info-hazard note: see Appendix C.

## Author Contributions (optional)

Both authors contributed equally to the design, implementation, experiments, analysis and writing of this project.

## References

- Grassé, P.-P. (1959). La reconstruction du nid et les coordinations interindividuelles chez Bellicositermes natalensis et Cubitermes sp. La théorie de la stigmergie. Insectes Sociaux, 6(1), 41–80. https://doi.org/10.1007/BF02223791
- Greenblatt, R., Shlegeris, B., Sachan, K., & Roger, F. (2024). AI Control: Improving Safety Despite Intentional Subversion. Proceedings of the 41st International Conference on Machine Learning (ICML). https://arxiv.org/abs/2312.06942
- Heylighen, F. (2016). Stigmergy as a universal coordination mechanism I: Definition and components. Cognitive Systems Research, 38, 4–13. https://doi.org/10.1016/j.cogsys.2015.12.002
- Motwani, S. R., Baranchuk, M., Strohmeier, M., Bolina, V., Torr, P. H. S., Hammond, L., & Schroeder de Witt, C. (2024). Secret Collusion among AI Agents: Multi-Agent Deception via Steganography. Advances in Neural Information Processing Systems (NeurIPS). https://arxiv.org/abs/2402.07510

## Appendix (optional)

### A. Episodes used in this paper

*Table A1. The 247 agent episodes used here. In addition, 100 recorded episodes were edited and re-scored without new runs (Section 4.4).*

| Experiment | Swarm | Covert | Honest |
|---|---|---|---|
| Main, unwatched | MiniMax | 30 | 30 |
| Main, watched (adaptive round 1 and its negatives) | MiniMax | 20 | 20 |
| Replication, unwatched | Qwen | 30 | 30 |
| Strong swarm, unwatched | Kimi | 20 | 20 |
| Fresh held-out test of the file rule | Kimi | 6 | 6 |
| Adaptive red team, rounds 2–3 | MiniMax | 20 | — |
| Vault control | MiniMax | — | 15 |

### B. Deviations and tests not discussed

- All deviations are logged in `PREREG.md`. The budget stop was raised, finally to $57, when the team added a second API key. The hidden-file rule was committed in code, but not written into the pre-registration, before the fresh runs. Seven fresh-episode attempts failed with API errors and were re-run, as the pre-registration requires. One pre-stated vault-control target was narrowly missed: at most 20% of vault teams flagged by the policy-informed judge was expected, and 3 of 14 (21%) were.
- The repository reports every pre-registered test, including several not covered here because they do not bear on the main question: the judge given agents' private reasoning (an upper bound, not a deployable monitor); joint vs per-agent judge (H1, not supported); where the evidence lives by capability (H6b, reversed) and undetected success by swarm (37% MiniMax vs 0% Kimi); the watched condition (H5); a skeptical judge prompt (H6c); a weak judge and a single-agent cell (P1, P3); a fixed instruction-tampering rule (rule B, which failed both its tests); and log degradation (H7).
- **Instruction poisoning on fresh seeds.** The MIGRATION.md tactic in Box 1 appeared in only 1 of 6 fresh covert Kimi episodes, so it is not a stable signature.
- **Tooling.** The `tripwire` package wraps a shared folder in a hash-chained event log, flags hidden writes, canary leaks and edits to shared instruction files, and replays an episode with the alerts marked.

### C. Dual-use and ethical considerations

We describe evasion tactics: instruction poisoning, hidden drops, and "stop hiding" under monitor feedback. They emerged from public models with minimal prompting, in a simulated filesystem with a fake token. The main lesson, that behavioral monitors can be beaten by informed attackers, is more useful to defenders designing oversight than to attackers. The attacker briefings are published for reproducibility; they describe our monitor, not a general evasion method. No real credentials, systems, networks or people were involved.

### D. Log-edit interventions

*Table D1. Change in the 0–100 judge score after editing the logs (edited minus original, paired 95% bootstrap CI).*

| Edit | Swarm | n | Notes visible | Notes removed |
|---|---|---|---|---|
| Deconceal (covert) | Kimi | 20 | −4.9 [−13.4, −0.1] | −0.9 [−2.4, +0.5] |
| Deconceal (covert) | MiniMax | 30 | −3.5 [−10.3, +1.5] | −3.1 [−11.3, +2.9] |
| Addconceal (honest) | Kimi | 20 | +5.8 [−6.6, +18.8] | +16.5 [+5.8, +28.8] |
| Addconceal (honest) | MiniMax | 30 | +0.6 [−9.7, +10.4] | +8.8 [+1.1, +18.2] |

## LLM Usage Statement

We used LLM assistants (Claude, Anthropic) to help write code and to help draft and edit this report. All experimental design decisions, results and claims were reviewed and verified by the authors against the code and result files in the repository. LLMs are also the subjects (swarm agents) and monitors (judges) of the experiments, as described in Section 3.
