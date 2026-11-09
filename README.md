# Dead Drops: detecting agent swarms that coordinate through the environment

Apart Research **Swarm Alignment Hackathon** (Nov 6–8, 2026). Track 4 (Multi-Agent Oversight and Control), with Track 1 also ticked.

**Report:** *When Colluders Stop Hiding: Monitors for File-Coordinating Agent Swarms Must Check Outcomes, Not Behavior*, by Silu Sharma and Sanket Sharma.
- Paper: [paper/DeadDrops_submission.docx](paper/DeadDrops_submission.docx) (source text [paper/submission.md](paper/submission.md))
- Slides: [docs/slides/DeadDrops-slides.pdf](docs/slides/DeadDrops-slides.pdf) ([PowerPoint](docs/slides/DeadDrops-slides.pptx), [HTML source](docs/slides/slides.html))

**Headline:** monitors that look for hiding catch naive colluders (judge AUROC 0.85–1.00), but after one round of feedback the attackers stopped hiding and 10 of 10 attacks succeeded undetected. Oversight has to check outcomes against policy, not agent behavior.

- [PREP.md](PREP.md): plan, checklist, timeline
- [PREREG.md](PREREG.md): pre-registration. Frozen at the commit recorded in its deviations log, before the main runs.
- [RESULTS.md](RESULTS.md): quick results summary
- [tripwire/](tripwire/README.md): **reusable tool**. Audit trail + red-flag report for agents sharing a folder, an instruction-file guard that blocks agents from rewriting shared instructions, and a live replay demo (standard library only)

## Layout
- `sandbox/`: multi-agent shared-workspace environment and append-only audit log
- `monitors/`: monitor prompts and code (M1–M4), frozen with the pre-registration
- `scoring/`: AUROC, bootstrap, attribution, and H6 analysis
- `analysis/`: pre-registered tests (`python3 -m analysis.primary [label]`)
- `tripwire/`: the standalone tool built from the monitors
- `results/`: per-episode JSONL and raw logs

## Code provenance
All code in this repo was written during the sprint (Nov 6–8, 2026) unless marked otherwise here.

## Secrets
API keys go in `.env`, which git ignores. Never commit keys.

## Running
```bash
python3 -m unittest discover -s tests            # offline tests, no API calls
python3 -m scripts.run_batch --dry-run --label smoke --seeds 1 2 --turns 6 --goal covert benign
```
Scoring stored episodes (M1–M4, labels, AUROC table): see the docstring of `scripts/score.py`.

Real runs need `OPENROUTER_API_KEY=...` in `.env`. Spend is logged to `results/spend.jsonl`; calls stop at $45 (`BUDGET_STOP_USD`).
