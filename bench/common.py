"""Shared paths and helpers for BlastRadius-Bench."""
import json, os, subprocess, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
WORK = ROOT / "work"          # cloned repos + per-repo venvs
DATA = ROOT / "data"          # generated tasks, graphs
RUNS = ROOT / "runs"          # model outputs / logs
for d in (WORK, DATA, RUNS):
    d.mkdir(exist_ok=True)

def load_repos(split=None):
    cfg = json.loads((ROOT / "bench" / "repos.json").read_text())
    out = []
    for s, lst in cfg.items():
        if split and s != split:
            continue
        for r in lst:
            r = dict(r); r["split"] = s; out.append(r)
    return out

def repo_dir(r): return WORK / r["name"]
def venv_py(r): return WORK / (r["name"] + ".venv") / "bin" / "python"

def run(cmd, cwd=None, timeout=None, env=None, check=False):
    p = subprocess.run(cmd, cwd=cwd, timeout=timeout, env=env, capture_output=True, text=True)
    if check and p.returncode != 0:
        sys.stderr.write(p.stdout[-3000:] + p.stderr[-3000:])
        raise RuntimeError(f"failed: {' '.join(map(str, cmd))}")
    return p

def jdump(obj, path):
    pathlib.Path(path).write_text(json.dumps(obj, indent=1))

def jl_write(rows, path):
    with open(path, "w") as f:
        for r in rows: f.write(json.dumps(r) + "\n")

def jl_read(path):
    with open(path) as f:
        return [json.loads(l) for l in f if l.strip()]
