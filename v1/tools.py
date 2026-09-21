import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from v0.tools import Tools as ReadTools


class ReadArgs(BaseModel):
    path: str = Field(description="Repository-relative UTF-8 file path")
    start: int = Field(default=1, ge=1, description="First line, 1-based")


class SearchArgs(BaseModel):
    query: str = Field(min_length=1, description="Literal text to locate")


class EditArgs(BaseModel):
    path: str
    old: str = Field(description="Exact unique text to replace; empty only to create a new file")
    new: str = Field(description="Replacement text")


class CommandArgs(BaseModel):
    argv: list[str] = Field(min_length=1, description="Executable and arguments, no shell syntax")


def command(root, argv, timeout=30):
    # 底层执行器没有审批：调用者必须先授权。argv 不经过 shell，但程序仍有用户权限。
    if not argv or any(not isinstance(arg, str) or "\x00" in arg for arg in argv):
        raise ValueError("Invalid argv")
    env = {k: v for k, v in os.environ.items()
           if not any(word in k.upper() for word in ("KEY", "TOKEN", "SECRET", "PASSWORD"))}
    # Rapid same-size edits can otherwise reuse timestamp-based Python bytecode.
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    with tempfile.TemporaryFile() as output:
        # 输出先落临时文件以限制内存占用；这不等于对磁盘输出设置了严格配额。
        process = subprocess.Popen(argv, cwd=root, env=env, stdin=subprocess.DEVNULL,
                                   stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
        timed_out = False
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
        finally:
            # Reap the whole process group, including background descendants.
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
        output.seek(0)
        text = output.read(12001).decode("utf-8", errors="replace")
    return {"exit_code": process.returncode, "timed_out": timed_out,
            "output": text[:12000], "truncated": len(text) > 12000}


class Tools(ReadTools):
    def __init__(self, root, approve=lambda argv: False):
        super().__init__(root)
        self.approve = approve
        self.items = [
            # StructuredTool 将函数说明、参数校验和调用接口组合；不隐藏外层循环。
            StructuredTool.from_function(self.read_file, args_schema=ReadArgs),
            StructuredTool.from_function(self.search, args_schema=SearchArgs),
            StructuredTool.from_function(self.list_files),
            StructuredTool.from_function(self.edit_file, args_schema=EditArgs),
            StructuredTool.from_function(self.run_command, args_schema=CommandArgs),
            StructuredTool.from_function(self.git_diff),
        ]

    def read_file(self, path, start=1):
        """Read at most 200 numbered source lines, bounded to the repository."""
        return super().execute("read_file", {"path": path, "start": start})

    def search(self, query):
        """Find literal text and return matching source paths and line numbers."""
        return super().execute("search", {"query": query})

    def list_files(self):
        """List up to 200 non-internal repository files."""
        return super().execute("list_files", {})

    def edit_file(self, path, old, new):
        """Replace one exact unique occurrence, or create a new file with empty old."""
        target = self.path(path)
        if len(new) > 100_000:
            raise ValueError("Replacement too large")
        if not target.exists():
            if old:
                raise ValueError("File does not exist; creation requires empty old")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(new, encoding="utf-8")
        else:
            if target.stat().st_size > 500_000:
                raise ValueError("File too large")
            text = target.read_text(encoding="utf-8")
            if not old or text.count(old) != 1:
                # 唯一匹配避免误改重复代码；内容漂移时应让模型重新读取而不是猜位置。
                raise ValueError("old must match exactly once; read the file again")
            target.write_text(text.replace(old, new, 1), encoding="utf-8")
        return json.dumps({"edited": path})

    def run_command(self, argv):
        """Run a command after human approval; use this for tests. Timeout: 30 seconds."""
        if not self.approve(argv):
            return json.dumps({"error": "Command denied by user"})
        return json.dumps(command(self.root, argv))

    def git_diff(self):
        """Show tracked repository changes; untracked files are listed separately."""
        diff = command(self.root, ["git", "--no-pager", "diff", "--no-ext-diff", "--no-textconv"])
        status = command(self.root, ["git", "status", "--short"])
        return json.dumps({"diff": diff, "status": status})

    def execute(self, name, args):
        try:
            item = next((tool for tool in self.items if tool.name == name), None)
            if item is None:
                raise ValueError(f"Unknown tool: {name}")
            return str(item.invoke(args))[:14000]
        except (ValueError, TypeError, OSError, KeyError) as exc:
            return json.dumps({"error": str(exc)})
