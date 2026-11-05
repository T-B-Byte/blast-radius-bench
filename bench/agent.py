"""ReAct agent for change-impact prediction, run against a local Ollama server.
Usage: python bench/agent.py --model MODEL --setting A|B|C [--repo NAME] [--limit N] [--tag TAG]"""
import argparse, json, re, time, urllib.request, os
from common import *
from graph import Tools

SYSTEM = """You are an expert Python engineer. A small code change (a unified diff) has been applied to a repository.
Your job: predict exactly which existing test functions will FAIL after this change (tests that passed before).
Be precise: include only tests that actually check behaviour the change breaks. If you believe no test fails, answer an empty list.
Reply with ONE JSON object per turn and nothing else.
{tool_text}To give your answer: {{"final": ["<test id>", ...]}} using test ids exactly as listed (file.py::test_name, or file.py::Class::test_name)."""

TOOL_TEXT = {
 "A": "",
 "B": """You may use tools first (at most {steps} steps). To call a tool: {{"tool": "<name>", "args": {{...}}}}
Tools:
- grep(pattern): fixed-string search over the repo's .py files, returns file:line:text
- read_file(path, start, end): read lines of a file
""",
 "C": """You may use tools first (at most {steps} steps). To call a tool: {{"tool": "<name>", "args": {{...}}}}
Tools (symbols look like "package.module:Class.method" or just a function name):
- callers(symbol, depth): static callers of a symbol, depth 1-3 (test functions appear as callers too)
- callees(symbol): functions a symbol calls
- tests_covering(symbol): tests that executed any line of this symbol in the unmodified repo
- show(symbol): source code of a symbol
""",
 "D": """The candidate tests below are exactly the tests whose execution covered the changed lines (coverage selection). Many of them still pass after the change.
Your job is to PRUNE: keep only candidates whose assertions this particular change actually breaks; drop candidates that merely execute the code.
You may use tools first (at most {steps} steps). To call a tool: {{"tool": "<name>", "args": {{...}}}}
Tools (symbols look like "package.module:Class.method" or just a function name):
- show(symbol): source code of a symbol (including test functions)
- callees(symbol): functions a symbol calls
""",
 "E": """The candidate tests below are exactly the tests whose execution covered the changed lines (coverage selection). Coverage selection has high recall: missing a truly failing test is far worse than keeping an extra one.
Your job is a CONSERVATIVE prune: start from ALL candidates and drop a candidate ONLY if you are highly confident (over 90% sure) that this change cannot alter any value its assertions check. If in doubt, KEEP it. Your final list should normally contain most of the candidates.
You may use tools first (at most {steps} steps). To call a tool: {{"tool": "<name>", "args": {{...}}}}
Tools (symbols look like "package.module:Class.method" or just a function name):
- show(symbol): source code of a symbol (including test functions)
- callees(symbol): functions a symbol calls
"""}
ALLOWED = {"A": set(), "B": {"grep", "read_file"}, "C": {"callers", "callees", "tests_covering", "show"}, "D": {"show", "callees"}, "E": {"show", "callees"}}

OBS_CAP = 6000
TASK_CAP = 1800

class CtxOverflow(Exception): pass

def chat(model, messages, host, think, timeout=900):
    body = {"model": model, "messages": messages, "stream": False,
            "options": {"temperature": 0, "num_ctx": 32768, "seed": 0}}
    if think: body["think"] = True
    req = urllib.request.Request(host + "/api/chat", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=max(30, timeout)) as r:
                d = json.loads(r.read())
            break
        except urllib.error.HTTPError as e:
            b = e.read().decode(errors="replace")
            if e.code == 400 and "context" in b: raise CtxOverflow(b)
            if e.code == 500 and attempt < 3:
                print(f"[retry-on-500] attempt {attempt+1}: {b[:200]}", flush=True); time.sleep(5); continue
            if e.code == 500:
                print(f"[retry-on-500] giving up, empty reply: {b[:200]}", flush=True)
                return "", 0, 0
            raise
    return d["message"]["content"], d.get("prompt_eval_count", 0), d.get("eval_count", 0)

def parse(text):
    t = re.sub(r"```(?:json)?", "", text)
    i = t.find("{")
    while i != -1:
        depth = 0
        for j in range(i, len(t)):
            depth += t[j] == "{"; depth -= t[j] == "}"
            if depth == 0:
                try: return json.loads(t[i:j + 1])
                except Exception: break
        i = t.find("{", i + 1)
    return None

def expand(pred, universe):
    out = set()
    for p in pred or []:
        p = str(p).strip()
        for u in universe:
            if u == p or u.startswith(p + "[") or u.startswith(p + "::"): out.add(u)
    return sorted(out)

def test_listing(task, stable, d, cap=12000):
    short = task["function"].split(":")[-1].split(".")[-1]
    files = {}
    for t in sorted(stable): files.setdefault(t.split("::")[0], []).append(t)
    def mentions(f):
        try: return short in (d / f).read_text()
        except Exception: return False
    order = sorted(files, key=lambda f: (not mentions(f), f))
    lines, n = [], 0
    for f in order:
        block = "\n".join(files[f])
        if n + len(block) > cap:
            lines.append(f"{f}: {len(files[f])} tests (not listed to save space)"); continue
        lines.append(block); n += len(block)
    return "\n".join(lines)

def run_task(task, r, tools, model, setting, host, steps, think, cands=None):
    stable = tools.stable
    if setting in ("D", "E"):
        if not cands:
            return {"id": task["id"], "pred_raw": [], "pred": [], "gold": task["failing_tests"], "prompt_tokens": 0, "completion_tokens": 0,
                    "tool_calls": 0, "parsed": True, "status": "no_candidates", "log": []}
        stable = set(cands)
        user = (f"Repository: {r['name']}\nChanged function: {task['function']}\n\nDiff:\n{task['diff']}\n\n"
                f"Coverage-selected candidate tests ({len(stable)}):\n" + "\n".join(sorted(stable)))
    else:
        user = (f"Repository: {r['name']}\nChanged function: {task['function']}\n\nDiff:\n{task['diff']}\n\n"
                f"Existing passing tests ({len(stable)}):\n{test_listing(task, stable, tools.d)}")
    sysmsg = SYSTEM.format(tool_text=TOOL_TEXT[setting].format(steps=steps))
    msgs = [{"role": "system", "content": sysmsg}, {"role": "user", "content": user}]
    log, ptok, ctok, calls, pred = [], 0, 0, 0, None
    t_start, status = time.time(), "ok"
    for step in range(steps + 1):
        left = TASK_CAP - (time.time() - t_start)
        if left <= 0: status = "timeout"; pred = None; break
        if step == steps:
            msgs.append({"role": "user", "content": 'Step limit reached. Give your final answer now as {"final": [...]}.'})
        try: text, p, c = chat(model, msgs, host, think, timeout=left); ptok += p; ctok += c
        except CtxOverflow: status = "ctx_overflow"; break
        except (TimeoutError, OSError) as e:
            if time.time() - t_start >= TASK_CAP - 5: status = "timeout"; break
            raise
        msgs.append({"role": "assistant", "content": text}); log.append(text[:2000])
        obj = parse(text)
        if isinstance(obj, dict) and "final" in obj:
            pred = obj["final"] if isinstance(obj["final"], list) else []; break
        if isinstance(obj, dict) and obj.get("tool") in ALLOWED[setting] and step < steps:
            calls += 1
            try: obs = getattr(tools, obj["tool"])(**(obj.get("args") or {}))
            except Exception as e: obs = f"(tool error: {e})"
            obs = str(obs)
            if len(obs) > OBS_CAP: obs = obs[:OBS_CAP] + f"\n... [truncated {len(obs) - OBS_CAP} chars; narrow your query]"
            msgs.append({"role": "user", "content": f"Observation:\n{obs}"}); continue
        msgs.append({"role": "user", "content": 'Invalid reply. Reply with one JSON object: a tool call or {"final": [...]}.'})
    return {"id": task["id"], "pred_raw": pred, "pred": expand(pred, stable), "gold": task["failing_tests"],
            "prompt_tokens": ptok, "completion_tokens": ctok, "tool_calls": calls, "parsed": pred is not None, "status": status, "log": log}

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True); ap.add_argument("--setting", choices="ABCDE", required=True)
    ap.add_argument("--repo"); ap.add_argument("--split"); ap.add_argument("--limit", type=int)
    ap.add_argument("--steps", type=int, default=15); ap.add_argument("--host", default="http://127.0.0.1:11434")
    ap.add_argument("--think", action="store_true"); ap.add_argument("--tag", default="")
    a = ap.parse_args()
    for r in load_repos(a.split):
        if a.repo and r["name"] != a.repo: continue
        tf = DATA / r["name"] / "tasks.jsonl"
        if not tf.exists(): continue
        tasks = jl_read(tf)[: a.limit] if a.limit else jl_read(tf)
        tools = Tools(r)
        cov = {x["id"]: x["pred"] for x in jl_read(RUNS / f"baseline-coverage__-__{r['name']}.jsonl")} if a.setting in ("D", "E") else {}
        safe = a.model.replace("/", "_").replace(":", "_")
        out = RUNS / f"{safe}__{a.setting}{a.tag}__{r['name']}.jsonl"
        done = {x["id"] for x in jl_read(out)} if out.exists() else set()
        with open(out, "a") as f:
            for t in tasks:
                if t["id"] in done: continue
                t0 = time.time(); res = run_task(t, r, tools, a.model, a.setting, a.host, a.steps, a.think, cov.get(t["id"]))
                res["secs"] = round(time.time() - t0, 1); res["model"] = a.model; res["setting"] = a.setting
                f.write(json.dumps(res) + "\n"); f.flush()
                print(f"{t['id']} {a.model} {a.setting}: pred={len(res['pred'])} gold={len(res['gold'])} calls={res['tool_calls']} {res['secs']}s", flush=True)
