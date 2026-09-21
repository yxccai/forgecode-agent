import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from langgraph.checkpoint.sqlite import SqliteSaver
from forgecode.config import Config
from forgecode.trace import Trace
from scripts.validate_coding import fixture
from scripts.validate_live import windows_environment
from v1.model import Model
from v1.tools import command
from v2.agent import initial
from v3.agent import Runtime
from v3.memory import Memory
from v3.tools import Tools


def main():
    windows_environment()
    config = Config.load(max_steps=15)
    with tempfile.TemporaryDirectory(prefix="forgecode-v3-") as root:
        fixture(root)
        for i in range(100):
            Path(root, f"component_{i}.py").write_text(f"def component_{i}(value):\n    return value * {i + 1}\n")
        events = []
        tools = Tools(root, lambda argv: argv == ["python3", "-m", "unittest", "discover"])
        with SqliteSaver.from_conn_string(":memory:") as saver:
            graph = Runtime(Model(config), tools, Trace(".forgecode/validation/v3.jsonl", events.append)).build(saver)
            result = graph.invoke(initial("Fix the add arithmetic function. Locate relevant symbols and tests. "
                "Run python3 -m unittest discover and inspect git_diff. Do not edit tests. "
                "Save a source-backed episodic memory of the fix and verification.", root, 15),
                {"configurable": {"thread_id": "v3"}, "recursion_limit": 200})
        assert result["status"] == "answered"
        assert command(root, ["python3", "-m", "unittest", "discover"])["exit_code"] == 0
        assert not command(root, ["git", "diff", "--", "test_app.py"])["output"]
        reads = {e["args"]["path"] for e in events if e["type"] == "tool_start" and e["name"] == "read_file"}
        assert len(reads) < 10, reads
        assert Memory(root).recall("add")
        usage = [e for e in events if e["type"] == "usage"]
        retrieval = next(e for e in events if e["type"] == "retrieval")
        print(json.dumps({"status": "passed", "indexed_files": retrieval["indexed_files"],
                          "selected_files": len(retrieval["selected"]), "files_read": sorted(reads),
                          "tool_calls": result["calls"], "tokens": result["tokens"],
                          "input_tokens": sum(e.get("input_tokens", 0) for e in usage)}, indent=2))


if __name__ == "__main__":
    main()
