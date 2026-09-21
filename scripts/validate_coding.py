"""Live coding acceptance on a disposable Git repository, independently verified."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.validate_live import windows_environment
from forgecode.config import Config
from forgecode.trace import Trace
from v1.agent import run
from v1.model import Model
from v1.tools import Tools, command


def fixture(root):
    Path(root, "app.py").write_text("def add(a, b):\n    return a - b\n")
    Path(root, "test_app.py").write_text(
        "import unittest\nfrom app import add\nclass Test(unittest.TestCase):\n"
        " def test_add(self): self.assertEqual(add(2, 3), 5)\n"
        " def test_negative(self): self.assertEqual(add(-2, -3), -5)\n")
    for argv in (["git", "init", "-q"], ["git", "add", "."],
                 ["git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                  "commit", "-qm", "fixture"]):
        subprocess.run(argv, cwd=root, check=True, capture_output=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--windows-env", action="store_true")
    args = parser.parse_args()
    if args.windows_env:
        windows_environment()
    config = Config.load(max_steps=15)
    with tempfile.TemporaryDirectory(prefix="forgecode-v1-") as root:
        fixture(root)
        events = []
        trace = Trace(".forgecode/validation/v1.jsonl", events.append)
        # Approval is narrowly pre-authorized for this disposable fixture's test command.
        allowed = lambda argv: argv in (["python3", "-m", "unittest", "discover"],
                                       ["python", "-m", "unittest", "discover"])
        run("Fix add in app.py. Inspect code, run python3 -m unittest discover, repair the bug, "
            "rerun tests and inspect git_diff. Do not modify test_app.py.",
            Model(config), Tools(root, allowed), trace, config.max_steps)
        check = command(root, ["python3", "-m", "unittest", "discover"])
        diff = command(root, ["git", "diff", "--", "app.py"])
        tests_diff = command(root, ["git", "diff", "--", "test_app.py"])
        assert check["exit_code"] == 0 and diff["output"] and not tests_diff["output"], check
        assert any(e["type"] == "tool_end" and e["name"] == "run_command" for e in events)
        print(json.dumps({"status": "passed", "verification": check, "diff": diff["output"],
                          "tool_calls": sum(e["type"] == "tool_end" for e in events)}, indent=2))


if __name__ == "__main__":
    main()
