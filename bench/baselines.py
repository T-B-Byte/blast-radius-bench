"""Non-LLM baselines: same-file, static reachability, clean-run line coverage.
Usage: python bench/baselines.py"""
import json, os
from common import *
from graph import Tools

def nodeid_prefixes(q, defs):
    mod, path = q.split(":"); dd = defs[q]
    return dd["file"] + "::" + path.replace(".", "::")

for r in load_repos():
    tf = DATA / r["name"] / "tasks.jsonl"
    if not tf.exists(): continue
    tools = Tools(r); defs = tools.g["defs"]; stable = sorted(tools.stable)
    test_files = sorted({t.split("::")[0] for t in stable})
    texts = {f: (repo_dir(r) / f).read_text() for f in test_files}
    outs = {k: [] for k in ("same_file", "reachability", "coverage")}
    for t in jl_read(tf):
        short = t["function"].split(":")[-1].split(".")[-1]
        sf = [x for x in stable if short in texts[x.split("::")[0]]]
        # reachability: transitive static callers (depth <= 5) that are test functions
        seen, frontier = set(), {t["function"]} if t["function"] in defs else set(tools._resolve(t["function"]))
        for _ in range(5):
            nxt = {c for q in frontier for c in tools.g["callers"].get(q, []) if c not in seen}
            seen |= nxt; frontier = nxt
        pref = {nodeid_prefixes(q, defs) for q in seen if q in defs}
        reach = [x for x in stable if any(x == p or x.startswith(p + "[") for p in pref)]
        cov = sorted(set(tools.line_tests.get(t["file"], {}).get(t["line"], [])) & tools.stable)
        for k, pred in (("same_file", sf), ("reachability", reach), ("coverage", cov)):
            outs[k].append({"id": t["id"], "pred": pred, "gold": t["failing_tests"], "prompt_tokens": 0, "completion_tokens": 0, "tool_calls": 0, "parsed": True})
    for k, rows in outs.items():
        jl_write(rows, RUNS / f"baseline-{k}__-__{r['name']}.jsonl")
    print(f"[baselines] {r['name']}: {len(rows)} tasks")
