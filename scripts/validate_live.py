"""Run a real V0 task; optionally import Windows user environment into this process."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from forgecode.config import Config
from forgecode.trace import Trace
from forgecode.windows import windows_environment
from v0.agent import run
from v0.model import Model
from v0.tools import Tools


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--windows-env", action="store_true")
    args = parser.parse_args()
    if args.windows_env:
        windows_environment()
    cfg = Config.load(max_steps=8)
    events = []
    trace = Trace(".forgecode/validation/v0.jsonl", events.append)
    answer = run("Inspect v0/agent.py and v0/tools.py. Explain how tool observations return to the "
                 "model and how paths outside the repository are rejected. Cite source lines.",
                 Model(cfg), Tools("."), trace, cfg.max_steps)
    used = [e["name"] for e in events if e["type"] == "tool_end"]
    if "read_file" not in used or not answer.strip():
        raise RuntimeError("Representative task did not read source and answer")
    print(json.dumps({"status": "passed", "tool_calls": len(used), "tools": used,
                      "trace": str(trace.path)}, indent=2))
    print(answer)


if __name__ == "__main__":
    main()
