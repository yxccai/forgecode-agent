import json
from pathlib import Path


class Tools:
    def __init__(self, root):
        self.root = Path(root).resolve()

    def path(self, name):
        # 先规范化 .. 和符号链接，再判断目录包含关系；字符串前缀判断不可靠。
        path = (self.root / name).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError("Path escapes repository")
        if any(part in {".git", ".forgecode", ".venv", "config.local.json"} or part.startswith(".env")
               for part in path.relative_to(self.root).parts):
            raise ValueError("Private or internal path")
        return path

    def files(self):
        # Do not follow symlinks or scan dependency/internal directories.
        import os
        for folder, dirs, names in os.walk(self.root):
            dirs[:] = sorted(d for d in dirs if not d.startswith(".") and d not in
                             {"node_modules", "__pycache__", "dist", "build"}
                             and not (Path(folder) / d).is_symlink())
            for name in sorted(names):
                p = Path(folder) / name
                if not name.startswith(".") and name != "config.local.json" and not p.is_symlink() and p.stat().st_size <= 500_000:
                    yield p

    @property
    def schemas(self):
        # Schema 是给模型看的接口声明；真正的路径与大小限制仍在 execute/path 中。
        specs = [
            ("read_file", "Read a UTF-8 file using 1-based start and at most 200 lines.",
             {"path": {"type": "string"}, "start": {"type": "integer", "minimum": 1}}, ["path"]),
            ("search", "Find literal text in repository files; returns paths and line numbers.",
             {"query": {"type": "string"}}, ["query"]),
            ("list_files", "List up to 200 repository file paths.", {}, []),
        ]
        return [{"type": "function", "function": {"name": n, "description": d,
                 "parameters": {"type": "object", "properties": p, "required": r,
                                "additionalProperties": False}}} for n, d, p, r in specs]

    def execute(self, name, args):
        try:
            if name == "read_file":
                start = int(args.get("start", 1))
                if start < 1:
                    raise ValueError("start must be positive")
                path = self.path(args["path"])
                if path.stat().st_size > 500_000:
                    raise ValueError("File exceeds 500 KB read limit")
                lines = path.read_text(encoding="utf-8").splitlines()
                result = "\n".join(f"{i + 1}: {line}" for i, line in
                                   enumerate(lines) if start <= i + 1 < start + 200)
            elif name == "list_files":
                from itertools import islice
                result = "\n".join(str(p.relative_to(self.root)) for p in islice(self.files(), 200))
            elif name == "search":
                matches = []
                for path in self.files():
                    try:
                        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                            if args["query"] in line:
                                matches.append(f"{path.relative_to(self.root)}:{i}: {line[:300]}")
                            if len(matches) >= 80:
                                break
                    except UnicodeError:
                        continue
                    if len(matches) >= 80:
                        break
                result = "\n".join(matches)
            else:
                raise ValueError(f"Unknown tool: {name}")
            return result[:12000]
        except (OSError, ValueError, KeyError, TypeError) as exc:
            return json.dumps({"error": str(exc)})
