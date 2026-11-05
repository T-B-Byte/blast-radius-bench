"""Static code graph (stdlib ast) + coverage-derived test edges, and the 4 agent tools.
Build: python bench/graph.py NAME  -> data/NAME/graph.json"""
import ast, json, os, sys
from collections import defaultdict
from common import *

def build(r):
    d = repo_dir(r); defs = {}; calls = defaultdict(set); name_index = defaultdict(set)
    for f in sorted(d.rglob("*.py")):
        rel = os.path.relpath(f, d)
        if rel.startswith((".", "build/", "docs/")) or ".venv" in rel: continue
        try: tree = ast.parse(f.read_text())
        except Exception: continue
        mod = rel[:-3].replace("/", ".").removesuffix(".__init__")
        aliases = {"self", "cls"}
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                aliases |= {(a.asname or a.name).split(".")[0] for a in n.names}
            elif isinstance(n, ast.ImportFrom):
                aliases |= {a.asname or a.name for a in n.names}
        def walk(node, stack, cur):
            for ch in ast.iter_child_nodes(node):
                if isinstance(ch, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    q = f"{mod}:{'.'.join(stack + [ch.name])}"
                    defs[q] = {"file": rel, "start": ch.lineno, "end": ch.end_lineno, "kind": type(ch).__name__}
                    name_index[ch.name].add(q)
                    walk(ch, stack + [ch.name], q if not isinstance(ch, ast.ClassDef) else cur)
                else:
                    if isinstance(ch, ast.Call) and cur:
                        fn = ch.func
                        nm = fn.id if isinstance(fn, ast.Name) else None
                        if isinstance(fn, ast.Attribute) and isinstance(fn.value, ast.Name) and fn.value.id in aliases:
                            nm = fn.attr  # module.func() or self.method(); skip obj.method() on unknown receivers
                        if nm: calls[cur].add(nm)
                    elif isinstance(ch, ast.Name) and cur and isinstance(ch.ctx, ast.Load):
                        calls[cur].add(ch.id)  # function passed as value (e.g. map(f, ...)) counts as a reference
                    walk(ch, stack, cur)
        walk(tree, [], None)
    callees = {q: sorted(t for nm in calls.get(q, ()) for t in name_index.get(nm, ()) if t != q) for q in defs}
    callers = defaultdict(set)
    for q, cs in callees.items():
        for c in cs: callers[c].add(q)
    return {"defs": defs, "callees": callees, "callers": {k: sorted(v) for k, v in callers.items()}}

class Tools:
    """The tool API exposed to the agent (setting C) plus grep/read (setting B)."""
    CAP = 6000  # chars per observation (~1.5-2K tokens)
    def __init__(self, r):
        self.r, self.d = r, repo_dir(r)
        self.g = json.loads((DATA / r["name"] / "graph.json").read_text())
        lt = json.loads((DATA / r["name"] / "line_tests.json").read_text())
        self.line_tests = defaultdict(dict)
        for k, v in lt.items():
            f, ln = k.rsplit(":", 1); self.line_tests[f][int(ln)] = v
        self.stable = set(json.loads((DATA / r["name"] / "tests.json").read_text())["stable"])
    def _cap(self, s): return s if len(s) <= self.CAP else s[:self.CAP] + f"\n...[truncated {len(s)-self.CAP} chars]"
    def _resolve(self, symbol):
        if symbol in self.g["defs"]: return [symbol]
        tail = symbol.split(":")[-1]
        return [q for q in self.g["defs"] if q.endswith(":" + tail) or q.endswith("." + tail)][:10]
    def callers(self, symbol, depth=1):
        out, frontier, seen = [], set(self._resolve(symbol)), set()
        for lvl in range(1, min(int(depth), 3) + 1):
            nxt = set()
            for q in frontier:
                for c in self.g["callers"].get(q, []):
                    if c not in seen: seen.add(c); nxt.add(c); out.append(f"[depth {lvl}] {c}")
            frontier = nxt
        return self._cap("\n".join(out) or "(no static callers found)")
    def callees(self, symbol):
        out = [c for q in self._resolve(symbol) for c in self.g["callees"].get(q, [])]
        return self._cap("\n".join(out) or "(none)")
    def tests_covering(self, symbol):
        res = set()
        for q in self._resolve(symbol):
            dd = self.g["defs"][q]
            for ln in range(dd["start"], dd["end"] + 1):
                res |= set(self.line_tests.get(dd["file"], {}).get(ln, []))
        res = sorted(t for t in res if t in self.stable)
        return self._cap("\n".join(res) or "(no tests execute this symbol)")
    def show(self, symbol):
        out = []
        for q in self._resolve(symbol)[:3]:
            dd = self.g["defs"][q]; lines = (self.d / dd["file"]).read_text().split("\n")
            out.append(f"# {q} ({dd['file']}:{dd['start']})\n" + "\n".join(lines[dd["start"] - 1: dd["end"]]))
        return self._cap("\n\n".join(out) or f"(symbol not found: {symbol})")
    def grep(self, pattern):
        p = run(["grep", "-rnI", "--include=*.py", "-F", str(pattern), "."], cwd=self.d)
        lines = [l for l in p.stdout.split("\n") if l and ".venv" not in l][:80]
        return self._cap("\n".join(lines) or "(no matches)")
    def read_file(self, path, start=1, end=200):
        f = (self.d / path).resolve()
        if not str(f).startswith(str(self.d.resolve())) or not f.exists(): return "(file not found)"
        lines = f.read_text().split("\n"); s, e = max(1, int(start)), min(len(lines), int(end))
        return self._cap("\n".join(f"{i}: {lines[i-1]}" for i in range(s, e + 1)))

if __name__ == "__main__":
    r = [x for x in load_repos() if x["name"] == sys.argv[1]][0]
    (DATA / r["name"]).mkdir(exist_ok=True); g = build(r); jdump(g, DATA / r["name"] / "graph.json")
    print(f"[graph] {r['name']}: {len(g['defs'])} defs, {sum(len(v) for v in g['callees'].values())} edges")
