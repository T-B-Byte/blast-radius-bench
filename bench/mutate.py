"""AST-located, single-line text mutations inside function bodies (no hand labels)."""
import ast, random

CMP = {"<": "<=", "<=": "<", ">": ">=", ">=": ">", "==": "!=", "!=": "==", "is": "is not", "is not": "is", "in": "not in", "not in": "in"}
BIN = {ast.Add: ("+", "-"), ast.Sub: ("-", "+"), ast.Mult: ("*", "//"), ast.FloorDiv: ("//", "*")}

def _seg(lines, l1, c1, l2, c2):
    if l1 != l2: return None
    return lines[l1 - 1][c1:c2]

class _V(ast.NodeVisitor):
    def __init__(self, lines, modname):
        self.lines, self.mod, self.stack, self.fn, self.out = lines, modname, [], [], []
    def _scope(self, node):
        self.stack.append(node.name)
        is_fn = isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        if is_fn: self.fn.append(".".join(self.stack))
        body = node.body
        if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant) and isinstance(body[0].value.value, str):
            body = body[1:]
        for b in body: self.visit(b)
        if is_fn: self.fn.pop()
        self.stack.pop()
    visit_FunctionDef = visit_AsyncFunctionDef = visit_ClassDef = _scope
    def add(self, line, c1, c2, new, op):
        if not self.fn: return
        old = self.lines[line - 1][c1:c2]
        if old == new: return
        self.out.append({"function": f"{self.mod}:{self.fn[-1]}", "line": line, "c1": c1, "c2": c2, "old": old, "new": new, "op": op})
    def visit_Compare(self, n):
        if len(n.ops) == 1:
            r = n.comparators[0]
            s = _seg(self.lines, n.left.end_lineno, n.left.end_col_offset, r.lineno, r.col_offset)
            if s is not None:
                tok = " ".join(s.replace("(", " ").replace(")", " ").split())
                if tok in CMP and "(" not in s and ")" not in s:
                    lead = len(s) - len(s.lstrip()); trail = len(s) - len(s.rstrip())
                    self.add(n.left.end_lineno, n.left.end_col_offset + lead, r.col_offset - trail, CMP[tok], "cmp_flip")
        self.generic_visit(n)
    def visit_BoolOp(self, n):
        a, b = n.values[0], n.values[1]
        s = _seg(self.lines, a.end_lineno, a.end_col_offset, b.lineno, b.col_offset)
        if s is not None and s.strip() in ("and", "or"):
            c1 = a.end_col_offset + len(s) - len(s.lstrip())
            self.add(a.end_lineno, c1, c1 + len(s.strip()), "or" if s.strip() == "and" else "and", "bool_swap")
        self.generic_visit(n)
    def visit_BinOp(self, n):
        if type(n.op) in BIN:
            sym, rep = BIN[type(n.op)]
            s = _seg(self.lines, n.left.end_lineno, n.left.end_col_offset, n.right.lineno, n.right.col_offset)
            if s is not None and s.strip() == sym:
                c1 = n.left.end_col_offset + len(s) - len(s.lstrip())
                self.add(n.left.end_lineno, c1, c1 + len(sym), rep, "arith_swap")
        self.generic_visit(n)
    def visit_UnaryOp(self, n):
        if isinstance(n.op, ast.Not) and n.lineno == n.operand.lineno:
            self.add(n.lineno, n.col_offset, n.operand.col_offset, "", "not_drop")
        self.generic_visit(n)
    def visit_Constant(self, n):
        if type(n.value) is int and n.lineno == n.end_lineno:
            self.add(n.lineno, n.col_offset, n.end_col_offset, str(n.value + 1), "const_off_by_one")
    def visit_Return(self, n):
        v = n.value
        if v is not None and not (isinstance(v, ast.Constant) and v.value is None) and v.lineno == v.end_lineno:
            self.add(v.lineno, v.col_offset, v.end_col_offset, "None", "return_none")
        self.generic_visit(n)

def mutants_for_file(path, modname):
    src = open(path).read(); lines = src.split("\n")
    try: tree = ast.parse(src)
    except SyntaxError: return []
    v = _V(lines, modname); v.visit(tree)
    for m in v.out: m["file"] = str(path)
    return v.out

def apply(src_text, m):
    lines = src_text.split("\n"); L = lines[m["line"] - 1]
    assert L[m["c1"]:m["c2"]] == m["old"], "stale mutant"
    lines[m["line"] - 1] = L[:m["c1"]] + m["new"] + L[m["c2"]:]
    out = "\n".join(lines)
    ast.parse(out)
    return out

def sample(muts, k, seed=0):
    rng = random.Random(seed); by = {}
    for m in muts: by.setdefault(m["op"], []).append(m)
    for v in by.values(): rng.shuffle(v)
    out, ops = [], sorted(by)
    while len(out) < k and any(by.values()):
        for o in ops:
            if by[o] and len(out) < k: out.append(by[o].pop())
    return out
