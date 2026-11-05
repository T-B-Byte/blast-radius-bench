# BlastRadius-Bench

Mutation-labeled benchmark for **test-level change-impact prediction**, with Gemma 4 agent baselines.

> This entry was made by Tina Bean with the help of AI, using her own compute power, time, and resources.

**Status:** draft package for the Kaggle Gemma 4 Developer Agent Paper Track. **Not published.** Numbers freeze 2026-11-08. Paper due 2026-11-12 11:59 PM UTC.

## Framing
Pre-registered rule: an LLM pruning setting is the headline only if it beats coverage F1 on at least 2 of 3 held-out repos. Settings **D** (coverage-then-prune) and **E** (conservative prune) each beat coverage on **0 of 3**. This release is offered as a **Best New Resource** plus a **negative result** for LLM pruning under F1. We claim **no novelty over TestPrune (arXiv:2510.18270)** beyond this benchmark and the measured precision/recall trade-off.

## Logged headline numbers (held-out, 26B-A4B, n=50/repo)
| System | browser-harness F1 | cost-xray F1 | grip F1 | pooled P / R / F1 |
|---|---|---|---|---|
| Coverage | **0.759** | **0.595** | **0.595** | 0.461 / 1.000 / **0.631** |
| D_v2 | 0.472 | 0.436 | 0.275 | 0.840 / 0.239 / 0.372 |
| E_v2 | 0.519 | 0.467 | 0.325 | 0.735 / 0.291 / 0.417 |

Sources: `logs/E_v2_per_repo_2026-11-04.log`, `logs/D_v2_per_repo_2026-11-04.log`, `logs/scores_heldout_v2_E_2026-11-04.txt`.

## Layout
- `bench/` — prepare, mutate, label, baselines, agent, score, compare50
- `data/<repo>/tasks.jsonl` — held-out tasks for browser-harness, cost-xray, grip
- `runs/` — per-task predictions (transcript `log` field stripped)
- `logs/` — scored tables with bootstrap CIs
- `scripts/` — example run scripts (edit host/model as needed)

## Quick start (local Ollama)
```bash
# requires: Python 3.12+, Ollama with hf.co/google/gemma-4-26B-A4B-it-qat-q4_0-gguf
python bench/score.py --split heldout
python bench/compare50.py
```
Full regenerate of mutants needs the upstream pytest repos checked out under `work/` (see `scripts/build_heldout.sh`). That step is heavy; the checked-in `data/` and `runs/` are enough to rescore.

## License
Licensed under the **Apache License 2.0**. See `LICENSE`.

## Authorship
This entry was made by Tina Bean with the help of AI, using her own compute power, time, and resources. Not sole-authored. See the paper draft Section 9 for the who-did-what split (confirmed by Tina Bean).
