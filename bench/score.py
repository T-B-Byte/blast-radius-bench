"""Score all runs: micro/macro P/R/F1 with 95% bootstrap CIs, exact match, all-clear accuracy, cost.
Usage: python bench/score.py [--split heldout] -> prints a table and writes runs/scores.json"""
import argparse, collections, json, random
from common import *

def prf(p, g):
    p, g = set(p), set(g); tp = len(p & g)
    P = tp / len(p) if p else (1.0 if not g else 0.0)
    R = tp / len(g) if g else 1.0
    F = 2 * P * R / (P + R) if P + R else 0.0
    return tp, len(p), len(g), P, R, F

def agg(rows):
    tp = sum(prf(r["pred"], r["gold"])[0] for r in rows); np_ = sum(len(r["pred"]) for r in rows); ng = sum(len(r["gold"]) for r in rows)
    P = tp / np_ if np_ else 0.0; R = tp / ng if ng else 0.0; F = 2 * P * R / (P + R) if P + R else 0.0
    return P, R, F, sum(prf(r["pred"], r["gold"])[5] for r in rows) / len(rows)

ap = argparse.ArgumentParser(); ap.add_argument("--split"); a = ap.parse_args()
split_of = {r["name"]: r["split"] for r in load_repos()}
groups = collections.defaultdict(list)
for f in sorted(RUNS.glob("*.jsonl")):
    sysname, _, repo = f.stem.partition("__")[0], None, f.stem.rsplit("__", 1)[-1]
    key = f.stem.rsplit("__", 1)[0]
    if a.split and split_of.get(repo) != a.split: continue
    groups[key] += jl_read(f)
res, rng = {}, random.Random(0)
print(f"{'system':42s} {'n':>4s} {'P':>6s} {'R':>6s} {'F1':>6s} {'F1 95% CI':>15s} {'macF1':>6s} {'EM':>5s} {'clear':>6s} {'tok/task':>9s} {'calls':>5s} {'parse':>5s}")
for k, rows in sorted(groups.items()):
    if not rows: continue
    P, R, F, mF = agg(rows)
    boots = sorted(agg([rows[rng.randrange(len(rows))] for _ in rows])[2] for _ in range(1000))
    em = sum(set(r["pred"]) == set(r["gold"]) for r in rows) / len(rows)
    empty = [r for r in rows if not r["gold"]]
    clear = sum(not r["pred"] for r in empty) / len(empty) if empty else float("nan")
    tok = sum(r["prompt_tokens"] + r["completion_tokens"] for r in rows) / len(rows)
    calls = sum(r["tool_calls"] for r in rows) / len(rows); parse = sum(r["parsed"] for r in rows) / len(rows)
    res[k] = dict(n=len(rows), P=P, R=R, F1=F, F1_ci=[boots[25], boots[974]], macroF1=mF, EM=em, all_clear=clear, tokens=tok, tool_calls=calls, parse_rate=parse)
    print(f"{k:42s} {len(rows):4d} {P:6.3f} {R:6.3f} {F:6.3f} {f'[{boots[25]:.3f},{boots[974]:.3f}]':>15s} {mF:6.3f} {em:5.2f} {clear:6.2f} {tok:9.0f} {calls:5.1f} {parse:5.2f}")
jdump(res, RUNS / "scores.json")
