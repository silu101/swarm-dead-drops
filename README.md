# Dead Drops: detecting agent swarms that coordinate through the environment

Apart Research **Swarm Alignment Hackathon** (Nov 6–8, 2026). Track 4 (Multi-Agent Oversight and Control), with Track 1 also ticked.

- [PREP.md](PREP.md): plan, checklist, timeline
- [PREREG.md](PREREG.md): pre-registration. Frozen at the commit recorded in its deviations log, before the main runs.

## Layout
- `sandbox/`: multi-agent shared-workspace environment and append-only audit log
- `monitors/`: monitor prompts and code (M1–M4), frozen with the pre-registration
- `scoring/`: AUROC, bootstrap, attribution, and H6 analysis
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
Real runs need `OPENROUTER_API_KEY=...` in `.env`. Spend is logged to `results/spend.jsonl`; calls stop at $45 (`BUDGET_STOP_USD`).
