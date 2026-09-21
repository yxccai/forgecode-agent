"""Interactive settings only. No dependency on agent state, tools or prompts."""
from dataclasses import asdict
from getpass import getpass
import json
import os
from pathlib import Path
import urllib.request


def choose(console, title, options, current="", custom=True):
    console.print(title, style="bold cyan", markup=False)
    for index, option in enumerate(options, 1):
        console.print(f"  {index}. {option}" + (" [current]" if option == current else ""), markup=False)
    console.print("  0. Cancel", style="dim")
    value = input("Number or value: " if custom else "Number: ").strip()
    if not value or value == "0":
        return current
    if value.isdigit() and 1 <= int(value) <= len(options):
        return options[int(value) - 1]
    if custom and not value.isdigit():
        return value
    raise ValueError("Invalid selection")


def pick_model(config, console):
    models = [config.model] if config.model else []
    if config.api_key:
        try:
            request = urllib.request.Request(config.base_url.rstrip("/") + "/models",
                headers={"Authorization": "Bearer " + config.api_key})
            with console.status("Loading provider models..."):
                with urllib.request.urlopen(request, timeout=10) as response:
                    payload = json.loads(response.read(1_000_000))
            models = sorted(set(models + [item["id"] for item in payload.get("data", [])
                                          if isinstance(item.get("id"), str)]))[:100]
        except Exception:
            console.print("Model list unavailable. Enter a model ID directly.", style="yellow")
    return choose(console, "Model", models, config.model)


def pick_effort(config, console):
    value = choose(console, "Reasoning effort (supported values depend on provider)",
                   ["default", "none", "minimal", "low", "medium", "high", "xhigh"],
                   config.reasoning_effort or "default")
    return None if value == "default" else value


def save(config, path):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        json.dump(asdict(config), stream, indent=2)
        stream.write("\n")
    target.chmod(0o600)


def api_menu(config, console, path):
    while True:
        action = choose(console, "API settings", ["Base URL", "API key", "Model", "Reasoning effort",
                                                    "Save and return", "Return without saving"], custom=False)
        if not action or action == "Return without saving":
            return
        if action == "Base URL":
            url = input("Base URL: ").strip()
            if url:
                if not url.startswith(("http://", "https://")):
                    raise ValueError("Base URL must start with http:// or https://")
                config.base_url = url
        elif action == "API key":
            value = getpass("API key (empty keeps current): ")
            if value:
                config.api_key = value
        elif action == "Model":
            config.model = pick_model(config, console)
        elif action == "Reasoning effort":
            config.reasoning_effort = pick_effort(config, console)
        elif action == "Save and return":
            save(config, path)
            console.print(f"Saved: {path}", markup=False)
            return
