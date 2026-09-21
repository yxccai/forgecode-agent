import json
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Config:
    base_url: str = "https://api.openai.com/v1"
    api_key: str = ""
    model: str = ""
    reasoning_effort: str | None = None
    max_steps: int = 20
    timeout: float = 90

    @classmethod
    def load(cls, path=None, **overrides):
        values = json.loads(Path(path).read_text()) if path else {}
        for key, suffix in (("base_url", "BASE_URL"), ("api_key", "API_KEY"),
                            ("model", "MODEL"), ("reasoning_effort", "REASONING_EFFORT")):
            value = os.getenv("FORGECODE_" + suffix) or os.getenv("OPENAI_" + suffix)
            if value:
                values[key] = value
        values.update({key: value for key, value in overrides.items() if value is not None})
        result = cls(**values)
        if not result.model:
            raise ValueError("Set FORGECODE_MODEL, OPENAI_MODEL or --model")
        if result.max_steps < 1 or result.timeout <= 0:
            raise ValueError("max_steps and timeout must be positive")
        return result


def configure(path="config.local.json"):
    """Keep secrets out of command arguments and create a private local config."""
    from getpass import getpass
    target = Path(path)
    values = json.loads(target.read_text()) if target.exists() else {}
    for key, prompt in (("base_url", "Base URL"), ("model", "Model"),
                        ("reasoning_effort", "Reasoning effort (provider-specific)")):
        value = input(f"{prompt} [{values.get(key) or ''}]: ").strip()
        if value:
            values[key] = value
    secret = getpass("API key (empty keeps existing): ")
    if secret:
        values["api_key"] = secret
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        json.dump(values, stream, indent=2)
        stream.write("\n")
    target.chmod(0o600)
    print(f"Saved {target}. Use --config {target}")
