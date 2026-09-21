import argparse
import json
from pathlib import Path
import shlex
import sys
from uuid import uuid4

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command
from forgecode.config import Config, configure
from forgecode.trace import Trace
from forgecode.ui import Terminal
from v1.model import Model
from v4.agent import Runtime, initial
from v4.tools import Tools
from v4.workspace import Workspace


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "configure":
        configure(sys.argv[2] if len(sys.argv) > 2 else "config.local.json")
        return
    parser = argparse.ArgumentParser(description="ForgeCode: isolated, persistent coding agent")
    parser.add_argument("task", nargs="?")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--thread")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--verify", help="Trusted verification command, e.g. 'python3 -m unittest discover'")
    parser.add_argument("--no-planning", action="store_true")
    parser.add_argument("--no-repo-context", action="store_true")
    parser.add_argument("--no-memory", action="store_true")
    parser.add_argument("--max-calls", type=int, default=60)
    parser.add_argument("--max-tokens", type=int, default=0)
    parser.add_argument("--max-repairs", type=int, default=3)
    for key in ("config", "base-url", "model", "reasoning-effort"):
        parser.add_argument("--" + key)
    parser.add_argument("--max-steps", type=int)
    args = parser.parse_args()
    if args.resume and not args.thread:
        parser.error("--resume requires --thread")
    if not args.resume and (not args.task or not args.verify):
        parser.error("New tasks require task and --verify; this command is pre-authorized for verification")
    if args.max_calls < 1 or args.max_tokens < 0 or args.max_repairs < 0:
        parser.error("Invalid budget")
    ui = Terminal()
    try:
        cfg = Config.load(args.config, base_url=args.base_url, model=args.model,
                          reasoning_effort=args.reasoning_effort, max_steps=args.max_steps)
        thread = args.thread or uuid4().hex[:12]
        workspace = Workspace(args.repo, thread)
        metadata = workspace.load() if args.resume else workspace.create(shlex.split(args.verify))
        ui.console.print(f"Thread: {thread}\nWorktree: {workspace.path}", markup=False)
        trace = Trace(workspace.data / "traces" / f"{thread}-{uuid4().hex[:8]}.jsonl", ui)
        tools = Tools(workspace.path, repo_context=not args.no_repo_context,
                      memory=not args.no_memory, store_root=workspace.root)
        with SqliteSaver.from_conn_string(str(workspace.data / "state-v4.sqlite")) as saver:
            graph = Runtime(Model(cfg), tools, trace, planning=not args.no_planning).build(saver)
            options = {"configurable": {"thread_id": thread}, "recursion_limit": 1000}
            snapshot = graph.get_state(options)
            if args.resume:
                if not snapshot.values or snapshot.values["root"] != str(workspace.path):
                    raise ValueError("No matching checkpoint")
                if not snapshot.next:
                    raise ValueError("Thread already finished")
                payload = None
            else:
                payload = initial(args.task, str(workspace.path), metadata["verify"], cfg.max_steps,
                                  args.max_calls, args.max_tokens, args.max_repairs)
            while True:
                snapshot = graph.get_state(options)
                pending = [item for task in snapshot.tasks for item in task.interrupts]
                if pending:
                    ui.close()
                    ui.console.print(json.dumps(pending[0].value, ensure_ascii=False), markup=False)
                    decision = input("Approve command? [y/N]: ").strip().lower() == "y"
                    payload = Command(resume=decision)
                result = graph.invoke(payload, options)
                if not result.get("__interrupt__"):
                    break
                payload = None
            patch = workspace.export()
            ui.console.print(f"Status: {result['status']}\nPatch: {patch}", markup=False)
            if result["status"] != "verified":
                raise RuntimeError("Task did not pass verification; worktree retained for inspection")
    except (Exception, KeyboardInterrupt) as exc:
        ui({"type": "error", "message": str(exc) or "Interrupted. Resume with the displayed thread ID."})
        raise SystemExit(1)
    finally:
        ui.close()


if __name__ == "__main__":
    main()
