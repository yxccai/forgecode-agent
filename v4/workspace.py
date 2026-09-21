import json
from pathlib import Path
import re
import subprocess


def git(root, *args, strip=True):
    result = subprocess.run(["git", *args], cwd=root, capture_output=True, timeout=30)
    if result.returncode:
        raise RuntimeError(result.stderr.decode(errors="replace"))
    output = result.stdout.decode("utf-8", errors="replace")
    return output.strip() if strip else output


class Workspace:
    def __init__(self, root, thread):
        if not re.fullmatch(r"[a-zA-Z0-9_-]{1,80}", thread):
            raise ValueError("Thread must contain 1-80 letters, numbers, underscores or hyphens")
        self.root = Path(root).resolve()
        if Path(git(self.root, "rev-parse", "--show-toplevel")).resolve() != self.root:
            raise ValueError("--repo must be the Git repository root")
        self.thread = thread
        self.data = self.root / ".forgecode"
        self.path = self.data / "worktrees" / thread
        self.manifest = self.data / "tasks" / f"{thread}.json"

    def create(self, verify):
        if self.manifest.exists() or self.path.exists():
            raise ValueError("Thread already exists; resume it or choose a new ID")
        if git(self.root, "status", "--porcelain", "--", ".", ":(exclude).forgecode"):
            raise ValueError("Commit or stash repository changes first; worktree starts at HEAD")
        if not verify:
            raise ValueError("An explicit verification command is required")
        head = git(self.root, "rev-parse", "HEAD")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        git(self.root, "worktree", "add", "--detach", str(self.path), head)
        self.manifest.parent.mkdir(parents=True, exist_ok=True)
        metadata = {"root": str(self.root), "worktree": str(self.path), "head": head, "verify": verify}
        self.manifest.write_text(json.dumps(metadata, indent=2))
        return metadata

    def load(self):
        metadata = json.loads(self.manifest.read_text())
        if metadata["root"] != str(self.root) or metadata["worktree"] != str(self.path):
            raise ValueError("Workspace metadata mismatch")
        if not self.path.is_dir() or Path(git(self.path, "rev-parse", "--show-toplevel")).resolve() != self.path:
            raise ValueError("Worktree missing or replaced")
        return metadata

    def export(self):
        patch = git(self.path, "--no-pager", "diff", "--binary", "--no-ext-diff", "--no-textconv", "HEAD", strip=False)
        from v0.tools import Tools
        guard = Tools(self.path)
        untracked = git(self.path, "ls-files", "--others", "--exclude-standard", "-z", strip=False).split("\0")
        for name in untracked:
            if not name:
                continue
            try:
                path = guard.path(name)
                if not path.is_file() or (self.path / name).is_symlink() or "__pycache__" in path.parts:
                    continue
            except ValueError:
                continue
            result = subprocess.run(["git", "diff", "--no-index", "--binary", "--no-ext-diff",
                                     "--", "/dev/null", name], cwd=self.path, capture_output=True, timeout=30)
            if result.returncode not in (0, 1):
                raise RuntimeError("Unable to export new file")
            patch += "\n" + result.stdout.decode("utf-8", errors="replace")
        target = self.data / "tasks" / f"{self.thread}.patch"
        target.write_text(patch)
        return target
