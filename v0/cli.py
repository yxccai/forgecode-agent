import argparse
from pathlib import Path
from uuid import uuid4

from forgecode.config import Config
from forgecode.trace import Trace
from forgecode.ui import Terminal
from v0.agent import run
from v0.model import Model
from v0.tools import Tools


def main():
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "configure":
        from forgecode.config import configure
        configure(sys.argv[2] if len(sys.argv) > 2 else "config.local.json")
        return
    parser = argparse.ArgumentParser(description="ForgeCode V0: repository inspection")
    parser.add_argument("task")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--config")
    parser.add_argument("--base-url")
    parser.add_argument("--model")
    parser.add_argument("--reasoning-effort")
    parser.add_argument("--max-steps", type=int)
    args = parser.parse_args()
    ui = Terminal()
    try:
        config = Config.load(args.config, base_url=args.base_url, model=args.model,
                             reasoning_effort=args.reasoning_effort, max_steps=args.max_steps)
        trace = Trace(Path(args.repo) / ".forgecode" / "traces" / f"{uuid4().hex}.jsonl", ui)
        run(args.task, Model(config), Tools(args.repo), trace, config.max_steps)
    except (Exception, KeyboardInterrupt) as exc:
        ui({"type": "error", "message": str(exc) or "Interrupted"})
        raise SystemExit(1)
    finally:
        ui.close()


if __name__ == "__main__":
    main()
