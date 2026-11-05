"""Generate BlastRadius-Bench tasks for one repo:
 1) 3 clean pytest runs -> stable passing tests (flaky removed)
 2) coverage with per-test contexts -> line -> tests map
 3) sample mutants in function bodies; run covering tests; label F = stable tests that fail.
Usage: python bench/label.py NAME [--n 200] [--timeout 120] [--seed 0]"""
import argparse, difflib, json, os, pathlib, random, time
from common import *
import mutate

ap = argparse.ArgumentParser(); ap.add_argument("name"); ap.add_argument("--n", type=int, default=200)
ap.add_argument("--timeout", type=int, default=120); ap.add_argument("--seed", type=int, default=0)
ap.add_argument("--empty-frac", type=float, default=0.15)
a = ap.parse_args()
r = [x for x in load_repos() if x["name"] == a.name][0]
d, py = repo_dir(r), str(venv_py(r))
out_dir = DATA / r["name"]; out_dir.mkdir(exist_ok=True)
BENCH = str(ROOT / "bench")
env = dict(os.environ, PYTHONPATH=BENCH + os.pathsep + os.environ.get("PYTHONPATH", ""), PYTHONDONTWRITEBYTECODE="1")

def pytest(extra, outfile, select=None, timeout=None):
    e = dict(env, BRB_OUT=str(outfile))
    if select is not None:
        sf = out_dir / "_select.json"; sf.write_text(json.dumps(sorted(select))); e["BRB_SELECT"] = str(sf)
    else:
        e.pop("BRB_SELECT", None)
    cmd = [py, "-m", "pytest", "-p", "brb_plugin", "-p", "no:cacheprovider", "-q", "--tb=no", "-x" if False else "-q", r["tests"]] + extra
    t = time.time()
    try:
        p = run(cmd, cwd=d, timeout=timeout, env=e)
    except Exception as ex:  # timeout
        return None, time.time() - t
    try:
        return json.loads(pathlib.Path(outfile).read_text()), time.time() - t
    except Exception:
        return {"results": {}, "collect_errors": ["<no output>"], "stderr": p.stderr[-2000:]}, time.time() - t

# 1) clean runs (+ coverage on run 1)
stable = None
for i in range(3):
    extra = ["--cov=" + r["pkg"], "--cov-context=test", "--cov-report="] if i == 0 else []
    res, dt = pytest(extra, out_dir / f"_clean{i}.json")
    passed = {k for k, v in res["results"].items() if v == "passed"}
    print(f"[clean {i}] {len(res['results'])} tests, {len(passed)} passed, {dt:.1f}s, collect_errors={len(res['collect_errors'])}")
    stable = passed if stable is None else stable & passed
    if i == 0: clean_secs = dt
all_tests = sorted(res["results"])
cj = out_dir / "coverage.json"
run([py, "-m", "coverage", "json", "--show-contexts", "-o", str(cj)], cwd=d, check=True)
cov = json.loads(cj.read_text())
line_tests = {}   # (relpath, line) -> set(nodeids)
for f, info in cov["files"].items():
    rel = os.path.relpath(os.path.join(d, f), d) if not os.path.isabs(f) else os.path.relpath(f, d)
    for ln, ctxs in info.get("contexts", {}).items():
        s = set()
        for c in ctxs:
            nid = c.rsplit("|", 1)[0]
            s.add(nid)  # "" = import/collection time
        line_tests[(rel, int(ln))] = s
jdump({"all_tests": all_tests, "stable": sorted(stable), "clean_secs": clean_secs}, out_dir / "tests.json")
jdump({f"{k[0]}:{k[1]}": sorted(v) for k, v in line_tests.items()}, out_dir / "line_tests.json")

# 2) mutants
pkg_root = d / r.get("src", "") / r["pkg"] if r.get("src") else d / r["pkg"]
cands = []
for f in sorted(pkg_root.rglob("*.py")):
    rel = os.path.relpath(f, d)
    if "/tests/" in "/" + rel or os.path.basename(rel).startswith("test_"):
        continue
    mod = rel[:-3].replace("/", ".").removesuffix(".__init__")
    cands += mutate.mutants_for_file(f, mod)
for m in cands: m["file"] = os.path.relpath(m["file"], d)
covered = [m for m in cands if line_tests.get((m["file"], m["line"]))]
uncovered = [m for m in cands if not line_tests.get((m["file"], m["line"]))]
print(f"[mutants] {len(cands)} candidates ({len(covered)} on covered lines, {len(uncovered)} uncovered)")
n_empty = int(round(a.n * a.empty_frac)); n_cov = a.n - n_empty
rng = random.Random(a.seed)
pool = mutate.sample(covered, len(covered), seed=a.seed)  # op-stratified ordering

tasks, stats = [], {"equivalent": 0, "timeout": 0, "crash": 0, "invalid": 0}
def make_task(m, F, ran):
    path = d / m["file"]; src = path.read_text(); new = mutate.apply(src, m)
    diff = "".join(difflib.unified_diff(src.splitlines(True), new.splitlines(True), "a/" + m["file"], "b/" + m["file"], n=3))
    return {"id": f"{r['name']}-{len(tasks):04d}", "repo": r["name"], "split": r["split"], "sha": None, "file": m["file"],
            "line": m["line"], "function": m["function"], "op": m["op"], "diff": diff, "failing_tests": sorted(F),
            "n_tests": len(stable), "ran_tests": ran}

t0 = time.time()
for m in pool:
    if len([t for t in tasks if t["failing_tests"]]) >= n_cov: break
    path = d / m["file"]; src = path.read_text()
    try: new = mutate.apply(src, m)
    except Exception: stats["invalid"] += 1; continue
    sel = line_tests[(m["file"], m["line"])]
    select = None if "" in sel else (sel & stable)
    if select is not None and not select: stats["equivalent"] += 1; continue
    path.write_text(new)
    try:
        res, dt = pytest([], out_dir / "_mut.json", select=select, timeout=a.timeout)
    finally:
        path.write_text(src)
    if res is None: stats["timeout"] += 1; continue
    if res["collect_errors"]: stats["crash"] += 1; continue
    F = {k for k, v in res["results"].items() if v == "failed" and k in stable}
    if not F: stats["equivalent"] += 1; continue
    tasks.append(make_task(m, F, len(select) if select is not None else len(stable)))
    if len(tasks) % 10 == 0: print(f"  {len(tasks)} tasks, {time.time()-t0:.0f}s elapsed, {stats}", flush=True)
for m in mutate.sample(uncovered, n_empty, seed=a.seed):
    try: tasks.append(make_task(m, set(), 0))
    except Exception: stats["invalid"] += 1
sha = run(["git", "rev-parse", "HEAD"], cwd=d).stdout.strip()
for t in tasks: t["sha"] = sha
assert run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=d).stdout.strip() == "", "repo left dirty!"
jl_write(tasks, out_dir / "tasks.jsonl")
jdump({"repo": r["name"], "tasks": len(tasks), "with_failures": sum(1 for t in tasks if t["failing_tests"]),
       "dropped": stats, "secs": round(time.time() - t0)}, out_dir / "label_stats.json")
print(f"[done] {r['name']}: {len(tasks)} tasks; dropped {stats}; {time.time()-t0:.0f}s")
