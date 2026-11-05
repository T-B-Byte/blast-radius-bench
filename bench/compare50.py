"""Per-repo micro F1 on the SAME task ids (first 50 per held-out repo) for every system. Usage: python bench/compare50.py"""
import collections, json
from common import *
REPOS = ["browser-harness", "cost-xray", "grip"]
ids = {r: [t["id"] for t in jl_read(DATA / r / "tasks.jsonl")[:50]] for r in REPOS}
def f1(rows):
    tp = sum(len(set(x["pred"]) & set(x["gold"])) for x in rows); np_ = sum(len(x["pred"]) for x in rows); ng = sum(len(x["gold"]) for x in rows)
    P = tp / np_ if np_ else 0.0; R = tp / ng if ng else 0.0
    return P, R, (2 * P * R / (P + R) if P + R else 0.0)
systems = sorted({f.stem.rsplit("__", 1)[0] for f in RUNS.glob("*.jsonl")})
print(f"{'system':55s} " + " ".join(f"{r:>24s}" for r in REPOS))
for s in systems:
    cells = []
    for r in REPOS:
        f = RUNS / f"{s}__{r}.jsonl"
        if not f.exists(): cells.append(f"{'-':>24s}"); continue
        m = {x["id"]: x for x in jl_read(f)}; rows = [m[i] for i in ids[r] if i in m]
        if not rows: cells.append(f"{'-':>24s}"); continue
        P, R, F = f1(rows); to = sum(x.get("status") == "timeout" for x in rows)
        cells.append(f"F1={F:.3f} n={len(rows):2d}/50 to={to:2d}")
    print(f"{s:55s} " + " ".join(f"{c:>24s}" for c in cells))
