"""Persist a live run, exit the worker, and resume in a fresh process."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from langgraph.checkpoint.sqlite import SqliteSaver
from forgecode.config import Config
from forgecode.trace import Trace
from scripts.validate_coding import fixture
from scripts.validate_live import windows_environment
from v1.model import Model
from v1.tools import Tools, command
from v2.agent import Runtime, initial


def worker(root, resume):
    windows_environment()
    cfg = Config.load(max_steps=15)
    with SqliteSaver.from_conn_string(str(Path(root, "state.sqlite"))) as saver:
        tools = Tools(root, lambda argv: argv == ["python3", "-m", "unittest", "discover"])
        graph = Runtime(Model(cfg), tools, Trace(".forgecode/validation/v2.jsonl")).build(saver, not resume)
        options = {"configurable": {"thread_id": "live-v2"}, "recursion_limit": 200}
        payload = None if resume else initial(
            "Inspect and fix app.py add. Run python3 -m unittest discover and inspect git_diff. "
            "Do not modify test_app.py.", root, max_steps=15)
        result = graph.invoke(payload, options)
        print(json.dumps({"phase": "resumed" if resume else "paused", "calls": result["calls"],
                          "status": result["status"], "next": list(graph.get_state(options).next)}))
        if not resume:
            assert graph.get_state(options).next
        else:
            assert result["status"] == "answered"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.worker:
        worker(args.worker, args.resume)
        return
    with tempfile.TemporaryDirectory(prefix="forgecode-v2-") as root:
        fixture(root)
        for resume in (False, True):
            argv = [sys.executable, __file__, "--worker", root] + (["--resume"] if resume else [])
            subprocess.run(argv, check=True)
        result = command(root, ["python3", "-m", "unittest", "discover"])
        assert result["exit_code"] == 0, result
        assert not command(root, ["git", "diff", "--", "test_app.py"])["output"]
        print(json.dumps({"status": "passed", "verification": result}))


if __name__ == "__main__":
    main()
