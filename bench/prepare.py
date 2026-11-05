"""Clone each repo at a pinned commit and build an isolated venv with uv.
Usage: python bench/prepare.py [--split dev|heldout] [--only NAME]"""
import argparse, json
from common import *

ap = argparse.ArgumentParser(); ap.add_argument("--split"); ap.add_argument("--only")
a = ap.parse_args()
pins = {}
pin_file = DATA / "pins.json"
if pin_file.exists(): pins = json.loads(pin_file.read_text())
for r in load_repos(a.split):
    if a.only and r["name"] != a.only: continue
    d = repo_dir(r)
    if not d.exists():
        run(["git", "clone", "--quiet", r["url"], str(d)], check=True)
    if r.get("ref", "HEAD") != "HEAD":
        run(["git", "checkout", "--quiet", r["ref"]], cwd=d, check=True)
    sha = run(["git", "rev-parse", "HEAD"], cwd=d).stdout.strip()
    first = run(["git", "log", "--reverse", "--format=%cI"], cwd=d).stdout.split("\n")[0]
    venv = WORK / (r["name"] + ".venv")
    if not venv.exists():
        run(["uv", "venv", "--quiet", "--python", "3.12", str(venv)], check=True)
    run(["uv", "pip", "install", "--quiet", "--python", str(venv_py(r))] + r["install"], cwd=d, check=True)
    pins[r["name"]] = {"sha": sha, "first_commit": first, "license": r["license"], "split": r["split"], "url": r["url"]}
    print(f"[prepare] {r['name']} @ {sha[:10]} (first commit {first[:10]})")
jdump(pins, pin_file)
