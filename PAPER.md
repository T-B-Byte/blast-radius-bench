# Can a Small Local Model Prune Coverage-Selected Tests? A Mutation-Labeled Benchmark for Test-Level Change-Impact Prediction with Gemma 4

*Subtitle: BlastRadius-Bench — a regenerable mutation-labeled resource; local Gemma 4 pruning raises precision but loses F1 to plain coverage on 3 of 3 held-out repos*

STATUS: DRAFT v2.2, Nov 4 2026, 9:35 PM ET (Steer final-review fixes). NOT SUBMITTED. Reviewer: Steer. Tina Bean submits herself.
Numbers freeze Nov 8. Section 6.4 (setting E) FILLED — LOSE (0 of 3). D cost-xray 0040–0049 re-run at num_ctx 32768 finished cleanly with identical predictions; Section 4 num_ctx inconsistency note dropped.

> **Authorship and AI use.** This entry was made by Tina Bean with the help of AI, using her own compute power, time, and resources. It is not the work of a sole author. See Section 9 for an exact split of who did what.

Source-of-truth logs (recorded locally in the project directory):
- `logs/scores_heldout_v2_E_2026-11-04.txt`: output of `bench/score.py --split heldout` and `bench/compare50.py` after E finished
- `logs/E_v2_per_repo_2026-11-04.log`: per-repo P/R/F1 with 95% bootstrap CIs on the same 50 tasks per repo for coverage, E_v2 and D_v2
- `logs/D_v2_per_repo_2026-11-04.log`: earlier D/B/C/coverage table including union-with-coverage rescoring
- Run logs: `logs/run_26B-A4B_E_heldout_v2_browser-harness.log` (second local machine), `logs/run_26B-A4B_E_heldout_v2_cost-xray.log` and `logs/run_26B-A4B_E_heldout_v2_grip.log` (first local machine); D logs as in v1

## Abstract
When a developer or an agent changes one function, which existing tests will fail? We release BlastRadius-Bench, a regenerable benchmark whose ground truth comes from mutation testing: a single-operator mutation is applied to one function, and the full suite records which previously passing tests now fail. We evaluate Gemma 4 E4B and Gemma 4 26B-A4B (QAT q4_0, served locally with Ollama on Apple M3 Ultra Mac Studios) under five settings — no tools (A), text-search tools (B), code-graph tools (C), coverage-then-prune (D), and conservative coverage-then-prune (E) — against non-LLM baselines. On a held-out split of three repositories (50 tasks each), agentic settings B and C reach pooled F1 0.185 and 0.188. Setting D doubles that to F1 0.372 (95% CI 0.289–0.462) with precision 0.840. Setting E (keep a candidate unless over 90% sure it is unaffected) raises recall to 0.291 and pooled F1 to 0.417 (95% CI 0.338–0.507), still below coverage's 0.631 on the same 150 tasks. Pre-registered rule: a pruning setting is the headline only if it beats coverage F1 on at least 2 of 3 repos. E and D each beat coverage on 0 of 3. We claim no method novelty over TestPrune (arXiv:2510.18270) beyond this benchmark and the measured precision/recall trade-off, and we offer the work as a Best New Resource with a negative result for LLM pruning under F1.

## 1. Introduction
Coding agents change code and then must decide what to re-run. Coverage-based regression test selection is safe (it keeps every test that executed the changed lines) but imprecise: on our held-out repos only 42–61% of coverage-selected tests actually fail. We ask whether a small open model running offline can supply the missing precision.

Contributions:
1. **BlastRadius-Bench**, an automatically regenerable, mutation-labeled benchmark for test-level change-impact prediction in Python, with a held-out split of repositories created after the model release (repos: grip, browser-harness, cost-xray).
2. **A controlled comparison** of two Gemma 4 sizes and five settings against coverage, reachability and same-file baselines, scored on identical task ids.
3. **A measured finding**: LLM pruning of coverage candidates raises precision (D 0.840, E 0.735) versus coverage's 0.461 but loses on F1 to coverage on 3 of 3 repos under the pre-registered 2-of-3 rule. Agentic exploration (B, C) under-predicts badly (recall about 0.11).

## 2. Related Work
- **Regression test selection and predictive test selection.** Machalica et al., *Predictive Test Selection*, ICSE-SEIP 2019 (https://arxiv.org/abs/1810.05286), learn a classifier from historical change/test outcomes. Google's *Regression Test Selection at Scale* (https://research.google/pubs/regression-test-selection-at-scale-4/) ranks client tests using call-graph features. These need history; ours is zero-shot.
- **LLM-guided test minimization.** TestPrune (arXiv:2510.18270, https://arxiv.org/abs/2510.18270) uses an LLM to predict suspicious functions from an issue and greedily selects a minimal coverage-based test subset, reporting 0.63 precision and 0.71 coverage recall on SWE-Bench. LTM (arXiv:2304.01397) minimizes suites using language-model similarity. Neither predicts which tests a given concrete diff breaks.
- **Mutation outcomes as prediction targets.** Predictive Mutation Testing (Zhang et al., ISSTA 2016, doi:10.1145/2931037.2931038). LLM critics for execution-free evaluation of code changes (Yadavally et al., 2025, arXiv:2501.16655). TEBench (Shang et al., 2026, arXiv:2605.06125) asks coding agents which tests a real commit breaks or makes stale, reporting identification F1 of 45.7–49.4%.
- Our contribution is narrower: a regenerable mutation-labeled benchmark with a post-release held-out split, and a same-task comparison of small local Gemma 4 agents against non-LLM selection baselines. **We claim no novelty over TestPrune beyond the benchmark and the measured precision/recall trade-off.**

## 3. Benchmark
- **Task.** Input: repository, changed function, unified diff, and the list of tests that pass before the change. Output: the set of test ids that fail after it.
- **Construction.** One mutation per task from six operators (arith_swap, not_drop, return_none, bool_swap, const_off_by_one, cmp_flip). Gold = tests that pass on the clean repo and fail on the mutant (`bench/mutate.py`, `bench/label.py`). Every held-out task in the first 50 per repo has at least one failing test.
- **Held-out repos** (first 50 of 150 tasks each, `data/<repo>/tasks.jsonl`): browser-harness (MIT, 283 tests, mean 4.26 gold tests/task), cost-xray (MIT, 215 tests, mean 3.82), grip (BSD-3-Clause, 579 tests, mean 8.16). Dev repos (toolz, more-itertools, boltons, cachetools, humanize) were used only for prompt development.

## 4. Settings and Baselines
- **A** no tools; **B** grep + read_file; **C** callers, callees, tests_covering, show (static and coverage graph); **D** coverage-then-prune: the coverage-selected tests are the candidates, the model may call show/callees, and its output is restricted to the candidates (`bench/agent.py`); **E** same as D, but the prompt requires a conservative prune: keep every candidate unless the model is over 90% sure the change cannot affect that test's assertions.
- **Baselines** (`bench/baselines.py`): coverage (tests that executed the changed lines), reachability (static call graph), same-file.
- **Models.** Gemma 4 E4B and 26B-A4B, `hf.co/google/gemma-4-*-it-qat-q4_0-gguf`, Ollama, temperature 0, seed 0, up to 15 tool steps.
- **Limits.** Each task is capped at 1,800 s wall clock; a timeout or context overflow is scored as an empty prediction. Tool observations are truncated to 6,000 characters.
- **Context window.** Setting D (including cost-xray-0040 to -0049) used num_ctx 32768. Those 10 cost-xray D tasks were re-run at 32768 on Nov 4, 9:05–9:30 PM ET (`logs/run_26B-A4B_D_heldout_v2_s1_costxray_32768.log`) after an earlier pass at 24576; predictions and statuses were identical, so D scores are unchanged. Setting E ran entirely at num_ctx 24576.
- **HTTP 500 handling.** On the first local machine, `bench/agent.py` retries a chat call up to 3 times on HTTP 500, waiting 5 s between attempts, then returns an empty reply counted as a failure (`[retry-on-500]` log lines). Logged `[retry-on-500]` event counts during E: browser-harness 0 (the second machine's agent lacked the retry loop; one raw HTTP 500 crashed the first pass, which was restarted and completed all 50 tasks), cost-xray 0, grip 5 (one chat recovered after a single retry; one chat exhausted 3 retries and returned empty).
- **Hardware.** Two Apple M3 Ultra Mac Studios, each with 512 GB unified memory (`sysctl hw.memsize` = 549755813888 on both), Ollama 0.40.9–0.40.10.
- **D run health** (from `runs/...__D_v2__*.jsonl`): browser-harness 48 ok, 1 context overflow, 1 timeout; cost-xray 50 ok; grip 47 ok, 1 context overflow, 2 timeouts. cost-xray tasks 0040-0049 were rerun at num_ctx 32768 with identical results.

## 5. Metrics
Micro precision, recall and F1 over test ids, per repo and pooled, on identical task ids (first 50 per held-out repo); 95% CIs from 1,000 task-level bootstrap resamples, seed 0 (`bench/score.py`, `bench/compare50.py`, `logs/E_v2_per_repo_2026-11-04.log`).

## 6. Results
### 6.1 Main table (held-out, 26B-A4B, n = 50 per repo; sources `logs/D_v2_per_repo_2026-11-04.log` and `logs/E_v2_per_repo_2026-11-04.log`)

| System | browser-harness P / R / F1 [95% CI] | cost-xray P / R / F1 [95% CI] | grip P / R / F1 [95% CI] | Pooled (n=150) P / R / F1 [95% CI] |
|---|---|---|---|---|
| Coverage | 0.612 / 1.000 / **0.759** [0.651, 0.856] | 0.424 / 1.000 / **0.595** [0.452, 0.741] | 0.423 / 1.000 / **0.595** [0.420, 0.776] | 0.461 / 1.000 / **0.631** [0.536, 0.734] |
| B_v2 (text tools) | 0.655 / 0.178 / 0.280 [0.090, 0.466] | 0.441 / 0.136 / 0.208 [0.118, 0.317] | 0.578 / 0.064 / 0.115 [0.042, 0.214] | 0.556 / 0.111 / 0.185 [0.113, 0.277] |
| C_v2 (graph tools) | 0.725 / 0.136 / 0.229 [0.132, 0.352] | 0.462 / 0.094 / 0.157 [0.082, 0.263] | 0.523 / 0.110 / 0.182 [0.092, 0.281] | 0.558 / 0.113 / 0.188 [0.134, 0.251] |
| D_v2 (coverage-then-prune) | 0.907 / 0.319 / 0.472 [0.272, 0.651] | 0.714 / 0.314 / 0.436 [0.295, 0.599] | 0.917 / 0.162 / 0.275 [0.203, 0.373] | 0.840 / 0.239 / 0.372 [0.289, 0.462] |
| E_v2 (conservative prune) | 0.818 / 0.380 / 0.519 [0.381, 0.675] | 0.628 / 0.372 / 0.467 [0.342, 0.600] | 0.771 / 0.206 / 0.325 [0.227, 0.454] | 0.735 / 0.291 / 0.417 [0.338, 0.507] |

Note on the coverage pooled figure: `score.py` reports coverage pooled F1 0.642 [0.572, 0.714] over all 450 held-out tasks; on the same 150 tasks the models ran, it is 0.631. The table uses 0.631 so all rows share task ids. The pooled B/C CIs here differ slightly from `score.py`'s (B 0.105–0.267, C 0.131–0.256) because the resampling order differs; point estimates match. E pooled CI from `score.py` is [0.338, 0.504]; the per-repo script reports [0.338, 0.507] — both logged.

D run health: browser-harness 48 ok, 1 timeout, 1 context overflow; cost-xray 50 ok; grip 47 ok, 2 timeouts, 1 context overflow.
E run health: browser-harness 50 ok; cost-xray 48 ok, 2 timeouts; grip 49 ok, 1 timeout.

Other held-out rows (`logs/scores_heldout_v2_E_2026-11-04.txt`, compare50, F1 per repo bh / cx / grip): 26B-A4B A 0.315 / 0.301 / 0.118; E4B A 0.302 / 0.255 / 0.155; E4B B 0.281 / 0.239 / 0.153; E4B C 0.287 / 0.256 / 0.135; reachability 0.191 / 0.231 / 0.224; same-file 0.059 / 0.124 / 0.114. Old partial 26B B and C rows (n = 5 and 6) are excluded.

### 6.2 Headline decision rule
Pre-registered rule: a pruning setting is the headline only if it beats coverage F1 on at least 2 of 3 repos. **D beats coverage on 0 of 3. E beats coverage on 0 of 3 (0.519 vs 0.759; 0.467 vs 0.595; 0.325 vs 0.595).** Neither is the headline. The paper is framed as a Best New Resource and a negative result for LLM pruning under F1.

### 6.3 Coverage ∪ model (zero-compute recall fix): fails
Re-scoring existing runs as (model prediction ∪ coverage) cannot raise recall above coverage's 1.000 and only adds false positives. Result (`logs/D_v2_per_repo_2026-11-04.log`): D∪cov equals coverage exactly (0.759 / 0.595 / 0.595), since D's output is a subset of the coverage candidates; B∪cov 0.737 / 0.568 / 0.594; C∪cov 0.751 / 0.579 / 0.581. Beats coverage on 0 of 3 repos.

### 6.4 Setting E, conservative prune — LOSE (filled Nov 4, 9:05 PM ET)
Same as D, but the prompt tells the model to keep every candidate unless it is over 90% sure the change cannot affect that test's assertions. Same 50 held-out tasks per repo, same model, num_ctx 24576. Logged results (`logs/E_v2_per_repo_2026-11-04.log`):

| Repo | E P | E R | E F1 [95% CI] | Coverage F1 | Beats cov? |
|---|---|---|---|---|---|
| browser-harness | 0.818 | 0.380 | 0.519 [0.381, 0.675] | 0.759 | no |
| cost-xray | 0.628 | 0.372 | 0.467 [0.342, 0.600] | 0.595 | no |
| grip | 0.771 | 0.206 | 0.325 [0.227, 0.454] | 0.595 | no |
| pooled (n=150) | 0.735 | 0.291 | 0.417 [0.338, 0.507] | 0.631 | — |

E improves on D's recall (0.239 → 0.291) and F1 (0.372 → 0.417) but still loses the 2-of-3 rule. Coverage remains the F1 winner on every repo.

### 6.5 Observations (from the table)
- Agentic exploration under-predicts: B and C reach about 0.56 precision but about 0.11 recall.
- Handing the model coverage candidates raises precision (D 0.840, E 0.735) and roughly doubles F1 versus B/C, but both pruning settings drop most of the truly failing tests relative to coverage's recall of 1.000.
- Conservative wording in E recovers some recall versus D, not enough to beat coverage F1 on any repo.
- grip, with the most failing tests per task (mean 8.16), is where pruning hurts most (E recall 0.206; D recall 0.162).

## 7. Discussion and Limitations
- F1 weights a missed failing test the same as an unnecessary run. In CI a miss is usually worse, which favors coverage. D/E's higher-precision points may still help when an agent must pick a few tests to show in a limited context. We have not measured that downstream effect.
- Three held-out repositories, 50 tasks each; CIs are wide and overlap between E and coverage on browser-harness and cost-xray.
- Mutants are single-operator and synthetic; real changes may differ.
- Quantized (q4_0) models, a single seed, and temperature 0.
- Setting E used num_ctx 24576 while D used 32768 (Section 4); HTTP 500 retry handling (Section 4).
- Closest prior method: TestPrune. We do not claim a better selector than TestPrune or than coverage; the logged contribution is the benchmark plus the measured trade-off.

## 8. Reproducibility
Code: `bench/` (prepare.py, mutate.py, label.py, baselines.py, agent.py, score.py, compare50.py). Commands are in `run_s1_D_costxray.sh`, `run_s2_D_bh.sh` and `run_E.sh` / `run_s2_E_bh.sh`. Raw per-task outputs are in `runs/*.jsonl`, with full model transcripts in the `log` field. Public notebook or repo link: DRAFTED under `packages/gemma4_repo/` (not published; awaiting Steer approval, then Tina's publish step). Winners must license under Apache 2.0; LICENSE in the draft package is a placeholder pending Tina's employment-agreement IP check.

## 9. Authorship and AI-use statement
This entry was made by Tina Bean with the help of AI, using her own compute power, time, and resources. Tina Bean is not the sole author of the text or code.

- **What Tina Bean did**: approved entering the contest, set the rules her AI assistants work under, owns and supplied the two Mac Studios and all compute, approved the contest entry and the authorship wording, and makes the final review and the submission herself.
- **What AI assistants did** (Grok Bot agents acting for her): wrote the benchmark and agent code, ran all experiments, computed every number and confidence interval, searched and checked related work, and drafted this text. A separate AI agent reviewed the drafts.
- **Models under study:** Gemma 4 E4B and 26B-A4B were the systems being evaluated, not authors.

## References
1. Machalica, M., et al. Predictive Test Selection. ICSE-SEIP 2019. arXiv:1810.05286.
2. Mehnaz, L., Wang, J., Stewart, B., Lee, D. J., Song, Z., Parker, R., Kavalerov, I. Regression Test Selection at Scale. ICSME 2026 Industry Track. https://research.google/pubs/regression-test-selection-at-scale-4/
3. TestPrune: Minimizing Regression Test Suites for Enhanced SWE Issue Reproduction and Resolution. arXiv:2510.18270.
4. Pan, R., Ghaleb, T. A., Briand, L. C. LTM: Scalable and Black-box Similarity-based Test Suite Minimization based on Language Models. arXiv:2304.01397.
5. Zhang, J., et al. Predictive Mutation Testing. ISSTA 2016. doi:10.1145/2931037.2931038.
6. Yadavally, A., Nguyen, H., Callot, L., Guinet, G. Large Language Model Critics for Execution-Free Evaluation of Code Changes. arXiv:2501.16655.
7. Shang, Y., et al. Breaking, Stale, or Missing? Benchmarking Coding Agents on Project-Level Test Evolution (TEBench). arXiv:2605.06125.
