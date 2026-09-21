"""Terminal REPL, slash commands and configuration; no agent decisions here."""
import argparse
from getpass import getpass
import json
import os
from pathlib import Path
import shlex
from uuid import uuid4

from langgraph.checkpoint.sqlite import SqliteSaver
from forgecode.config import Config
from forgecode.menus import api_menu, pick_effort, pick_model, save
from forgecode.session import Session
from forgecode.trace import Trace
from forgecode.ui import Terminal
from v1.model import Model


HELP = """/model [NAME]    Select or enter a model
/effort [LEVEL]  Select reasoning effort; 'default' omits the field
/api             Open API settings menu (URL, key, model, effort)
/url URL         Switch OpenAI-compatible endpoint
/key             Enter API key without echo
/config          Open API settings menu
/save            Save current settings for next launch
/verify COMMAND  Set trusted test command; 'off' disables automatic verification
/status          Show session and model, never the key
/resume          Continue an interrupted turn
/new             Start a fresh conversation
/exit            Exit
"""


def load_config(path=None, windows=False):
    if windows or (not path and not os.getenv("FORGECODE_MODEL") and not os.getenv("OPENAI_MODEL")
                   and not Path("config.local.json").exists()):
        try:
            from forgecode.windows import windows_environment
            windows_environment()
        except (OSError, RuntimeError, ValueError):
            if windows:
                raise
        except Exception:
            if windows:
                raise
    target = path or ("config.local.json" if Path("config.local.json").exists() else None)
    if target:
        # An explicitly selected interactive profile overrides inherited environment.
        values = json.loads(Path(target).read_text())
        result = Config.load(target, **{**values, "model": values.get("model") or "unconfigured"})
        result.model = values.get("model", "")
        return result
    try:
        return Config.load()
    except ValueError:
        result = Config.load(model="unconfigured")
        result.model = ""
        return result


def main():
    parser = argparse.ArgumentParser(description="ForgeCode interactive terminal")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--config")
    parser.add_argument("--windows-env", action="store_true")
    parser.add_argument("--session", help="Reopen a saved conversation ID")
    args = parser.parse_args()
    root = Path(args.repo).resolve()
    if not root.is_dir():
        parser.error("Repository directory does not exist")
    data = root / ".forgecode"
    data.mkdir(exist_ok=True)
    ui = Terminal()
    thread = args.session or uuid4().hex[:12]
    try:
        profile = Path(args.config) if args.config else data / "config.local.json"
        config = load_config(str(profile) if profile.exists() or args.config else None, args.windows_env)
        with SqliteSaver.from_conn_string(str(data / "interactive.sqlite")) as saver:
            def open_session():
                return Session(root, thread, saver, None,
                               Trace(data / "traces" / f"interactive-{thread}.jsonl", ui), config.max_steps)

            session = open_session()
            verify = session.snapshot().values.get("verify_argv", [])
            ui.console.print("ForgeCode", style="bold cyan")
            ui.console.print(f"{root}\nModel: {config.model or 'not configured'} | Session: {thread}", markup=False)
            ui.console.print("Edits affect this directory and require approval. /help for commands.", style="dim")

            def approve(request):
                ui.close()
                ui.console.print(json.dumps(request, ensure_ascii=False, indent=2), markup=False)
                return input("Approve? [y/N] ").strip().lower() == "y"

            while True:
                try:
                    text = input("\nforge> ").strip()
                    if not text:
                        continue
                    command, _, value = text.partition(" ")
                    value = value.strip()
                    if command in {"/exit", "/quit"}:
                        break
                    if command == "/help":
                        ui.console.print(HELP, markup=False)
                    elif command == "/status":
                        ui.console.print(f"Session: {thread}\nModel: {config.model}\n"
                                         f"Effort: {config.reasoning_effort or 'default'}\n"
                                         f"Verify: {shlex.join(verify) or 'off'}", markup=False)
                    elif command == "/new":
                        thread = uuid4().hex[:12]
                        session = open_session()
                        ui.console.print(f"Session: {thread}", markup=False)
                    elif command == "/verify":
                        if not value:
                            raise ValueError("Use /verify COMMAND or /verify off")
                        verify = [] if value == "off" else shlex.split(value)
                        ui.console.print(f"Verification: {shlex.join(verify) or 'off'}", markup=False)
                    elif command == "/save":
                        save(config, profile)
                        ui.console.print(f"Saved: {profile}", markup=False)
                    elif command in {"/model", "/effort", "/url", "/key", "/config", "/api"}:
                        if command == "/model":
                            config.model = value or pick_model(config, ui.console)
                        elif command == "/effort":
                            config.reasoning_effort = (None if value == "default" else value) if value else pick_effort(config, ui.console)
                        elif command == "/url":
                            config.base_url = value or input("Base URL: ").strip() or config.base_url
                        elif command == "/key":
                            config.api_key = getpass("API key: ")
                        else:
                            api_menu(config, ui.console, profile)
                        ui.console.print(f"Model: {config.model}; configuration updated", markup=False)
                    elif command.startswith("/") and command != "/resume":
                        raise ValueError("Unknown command; use /help")
                    else:
                        if not config.model:
                            ui.console.print("Model not configured. Use /api or /model.", style="yellow")
                            continue
                        session.runtime.model = Model(config)
                        session.turn(text, verify, approve, resume=command == "/resume")
                except EOFError:
                    break
                except KeyboardInterrupt:
                    ui.close()
                    ui.console.print("Interrupted. /resume to continue, /new to reset, /exit to quit.")
                except Exception as exc:
                    ui.close()
                    # Provider errors can echo endpoint details; keep credentials out of terminal logs.
                    message = str(exc) if isinstance(exc, ValueError) else type(exc).__name__ + ": request failed; /resume to retry"
                    if config.api_key:
                        message = message.replace(config.api_key, "[redacted]")
                    ui.console.print(message, style="red", markup=False)
    except (Exception, KeyboardInterrupt) as exc:
        ui.console.print(f"Startup failed: {type(exc).__name__}", style="red")
        raise SystemExit(1)
    finally:
        ui.close()


if __name__ == "__main__":
    main()
