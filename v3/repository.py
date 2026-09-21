import ast
import re
import subprocess
from pathlib import Path

from v0.tools import Tools


def terms(text):
    return set(re.findall(r"[a-zA-Z][a-zA-Z0-9]*", text.lower())) - {
        "the", "and", "with", "this", "that", "from", "test", "tests", "file", "fix"}


class Repository:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.guard = Tools(root)

    def paths(self):
        result = subprocess.run(["git", "ls-files", "-co", "--exclude-standard", "-z"],
                                cwd=self.root, capture_output=True, timeout=10)
        if result.returncode == 0:
            for name in sorted(set(result.stdout.decode("utf-8", errors="replace").split("\0"))):
                if not name:
                    continue
                try:
                    path = self.guard.path(name)
                    if path.is_file() and not (self.root / name).is_symlink() and path.stat().st_size <= 500_000:
                        yield path
                except (ValueError, OSError):
                    continue
        else:
            yield from self.guard.files()

    def index(self):
        records = []
        for path in self.paths():
            if len(records) >= 5000:
                break
            try:
                source = path.read_text(encoding="utf-8")
            except (UnicodeError, OSError):
                continue
            symbols, imports = [], []
            if path.suffix == ".py":
                try:
                    for node in ast.walk(ast.parse(source)):
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                            symbols.append({"name": node.name, "line": node.lineno, "kind": type(node).__name__})
                        elif isinstance(node, ast.Import):
                            imports.extend(alias.name for alias in node.names)
                        elif isinstance(node, ast.ImportFrom) and node.module:
                            imports.append(node.module)
                except SyntaxError:
                    pass
            records.append({"path": str(path.relative_to(self.root)), "symbols": symbols,
                            "imports": imports, "lines": len(source.splitlines()), "terms": terms(source)})
        return records

    def select(self, task, budget=8000):
        query = terms(task)
        records = self.index()
        def score(record):
            names = " ".join(s["name"] for s in record["symbols"])
            return (5 * len(query & terms(record["path"])) + 4 * len(query & terms(names)) +
                    len(query & record["terms"]))
        ranked = sorted(records, key=lambda item: (-score(item), item["path"]))
        selected, used = [], 0
        for record in ranked[:8]:
            clean = {key: value for key, value in record.items() if key != "terms"}
            clean["score"] = score(record)
            if not clean["score"]:
                continue
            import json
            size = len(json.dumps(clean))
            if used + size > budget:
                continue
            selected.append(clean)
            used += size
        return {"indexed_files": len(records), "selected": selected,
                "characters": used, "estimated_tokens": (used + 3) // 4}

    def symbols(self, query):
        results = []
        for record in self.index():
            for symbol in record["symbols"]:
                if query.lower() in symbol["name"].lower():
                    results.append({"path": record["path"], **symbol})
        return results[:60]
