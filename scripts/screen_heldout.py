"""Screen candidate held-out repos: first commit after 2026-03-31, permissive license,
pytest suite that passes (mostly) in < 60 s. Writes data/heldout_screen.json."""
import json, os, subprocess, sys, time, pathlib, tomllib
ROOT = pathlib.Path(__file__).resolve().parent.parent
W = ROOT / "work" / "_screen"; W.mkdir(parents=True, exist_ok=True)
cands = sys.argv[1:]
out = []
def sh(cmd, cwd=None, timeout=600):
    try: return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired: return None
for full in cands:
    name = full.split("/")[1]; d = W / name; rec = {"repo": full}
    try:
        if not d.exists(): sh(["git", "clone", "--quiet", f"https://github.com/{full}", str(d)], timeout=300)
        first = sh(["git", "log", "--reverse", "--format=%cI"], cwd=d).stdout.split("\n")[0]
        rec["first_commit"] = first
        tests = next((t for t in ("tests", "test") if (d / t).is_dir()), None); rec["tests"] = tests
        pkg = None
        if (d / "pyproject.toml").exists():
            try: pkg = tomllib.loads((d / "pyproject.toml").read_text()).get("project", {}).get("name")
            except Exception: pass
        rec["project"] = pkg
        if not tests or first < "2026-04-01": rec["verdict"] = "skip"; out.append(rec); print(rec, flush=True); continue
        v = d.parent / (name + ".venv")
        sh(["uv", "venv", "--quiet", "--python", "3.12", str(v)])
        py = str(v / "bin" / "python")
        ok = False
        for extra in ([".[test]"], [".[dev]"], ["."]):
            p = sh(["uv", "pip", "install", "--quiet", "--python", py, "-e"] + extra + ["pytest", "pytest-cov"], cwd=d)
            if p and p.returncode == 0: ok = True; rec["install"] = extra[0]; break
        if not ok: rec["verdict"] = "install_failed"; out.append(rec); print(rec, flush=True); continue
        t = time.time(); p = sh([py, "-m", "pytest", "-q", "--tb=no", "-p", "no:cacheprovider", tests], cwd=d, timeout=180)
        rec["secs"] = round(time.time() - t, 1)
        rec["summary"] = (p.stdout.strip().split("\n")[-1] if p else "TIMEOUT")
        rec["verdict"] = "candidate"
    except Exception as e:
        rec["verdict"] = f"error {e}"
    out.append(rec); print(rec, flush=True)
(ROOT / "data" / "heldout_screen.json").write_text(json.dumps(out, indent=1))
