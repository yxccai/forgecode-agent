import argparse
from pathlib import Path
import shlex
import sys
from uuid import uuid4

from langgraph.checkpoint.sqlite import SqliteSaver
from forgecode.config import Config, configure
from forgecode.trace import Trace
from forgecode.ui import Terminal
from v1.model import Model
from v1.tools import Tools
from v2.agent import Runtime, initial


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "configure":
        configure(sys.argv[2] if len(sys.argv) > 2 else "config.local.json")
        return
    parser = argparse.ArgumentParser(description="ForgeCode V2: persistent coding agent")
    parser.add_argument("task", nargs="?")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--thread", default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--pause-after-tool", action="store_true")
    parser.add_argument("--no-planning", action="store_true")
    parser.add_argument("--max-calls", type=int, default=60)
    parser.add_argument("--max-tokens", type=int, default=0)
    for key in ("config", "base-url", "model", "reasoning-effort"):
        parser.add_argument("--" + key)
    parser.add_argument("--max-steps", type=int)
    args = parser.parse_args()
    if args.resume and not args.thread:
        parser.error("--resume requires --thread")
    if not args.resume and not args.task:
        parser.error("task is required for a new thread")
    if args.max_calls < 1 or args.max_tokens < 0:
        parser.error("Invalid budget")
    root = Path(args.repo).resolve()
    data = root / ".forgecode"
    data.mkdir(exist_ok=True)
    thread = args.thread or uuid4().hex
    ui = Terminal()
    trace = Trace(data / "traces" / f"{uuid4().hex}.jsonl", ui)
    ui.console.print(f"Thread: {thread}", markup=False)
    try:
        config = Config.load(args.config, base_url=args.base_url, model=args.model,
                             reasoning_effort=args.reasoning_effort, max_steps=args.max_steps)
        def approve(argv):
            ui.close()
            return input(f"Execute {shlex.join(argv)}? [y/N] ").strip().lower() == "y"
        with SqliteSaver.from_conn_string(str(data / "state.sqlite")) as saver:
            runtime = Runtime(Model(config), Tools(root, approve), trace, not args.no_planning)
            graph = runtime.build(saver, args.pause_after_tool)
            options = {"configurable": {"thread_id": thread}, "recursion_limit": 1000}
            previous = graph.get_state(options)
            if args.resume:
                if not previous.values or previous.values["root"] != str(root):
                    raise ValueError("No matching thread for this repository")
                if not previous.next:
                    raise ValueError("Thread already finished; start a new thread")
                payload = None
            else:
                if previous.values:
                    raise ValueError("Thread already exists; use --resume")
                payload = initial(args.task, root, config.max_steps, args.max_calls, args.max_tokens)
            result = graph.invoke(payload, options)
            if graph.get_state(options).next:
                ui.console.print(f"Paused. Resume with --thread {thread} --resume", markup=False)
            elif result["status"] != "answered":
                raise RuntimeError(result["status"])
    except (Exception, KeyboardInterrupt) as exc:
        ui({"type": "error", "message": str(exc) or "Interrupted; resume this thread"})
        raise SystemExit(1)
    finally:
        ui.close()


if __name__ == "__main__":
    main()
