"""Live model fixes an off-by-one bug using an independent verifier and approvals."""
import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command
from forgecode.config import Config
from forgecode.trace import Trace
from scripts.validate_coding import fixture
from scripts.validate_live import windows_environment
from v1.model import Model
from v1.tools import command
from v4.agent import Runtime, initial
from v4.tools import Tools
from v4.workspace import Workspace, git


def main():
    windows_environment()
    with tempfile.TemporaryDirectory(prefix="forgecode-v4-") as folder:
        fixture(folder)
        workspace = Workspace(folder, "live")
        argv = ["python3", "-m", "unittest", "discover"]
        workspace.create(argv)
        events = []
        trace = Trace(".forgecode/validation/v4.jsonl", events.append)
        with SqliteSaver.from_conn_string(str(workspace.data / "state.sqlite")) as saver:
            graph = Runtime(Model(Config.load()), Tools(workspace.path, store_root=folder), trace).build(saver)
            opts = {"configurable": {"thread_id": "live"}, "recursion_limit": 200}
            result = graph.invoke(initial("Fix add in app.py. Run python3 -m unittest discover "
                "using run_command to check your work. Do not edit test_app.py.", str(workspace.path), argv), opts)
            approvals = 0
            while result.get("__interrupt__"):
                request = result["__interrupt__"][0].value
                allowed = request["argv"] == argv
                approvals += int(allowed)
                result = graph.invoke(Command(resume=allowed), opts)
        assert result["status"] == "verified", result["status"]
        assert approvals > 0, "No command approval was exercised"
        assert command(workspace.path, argv)["exit_code"] == 0
        assert not git(workspace.path, "diff", "--", "test_app.py")
        assert "a - b" in Path(folder, "app.py").read_text()
        patch = workspace.export()
        git(folder, "apply", "--check", str(patch))
        print(json.dumps({"status": result["status"], "approvals": approvals,
                          "baseline_exit": result["baseline"]["exit_code"],
                          "final_exit": result["verification"]["exit_code"],
                          "tool_calls": result["calls"], "tokens": result["tokens"],
                          "original_unchanged": True, "patch_applies": True}, indent=2))


if __name__ == "__main__":
    main()
