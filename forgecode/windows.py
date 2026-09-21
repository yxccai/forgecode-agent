"""Optional WSL bridge. Credentials stay in captured output and process memory."""
import json
import os
import subprocess


def windows_environment():
    script = """
    $result = @{}
    foreach ($name in @('FORGECODE_API_KEY', 'FORGECODE_BASE_URL', 'FORGECODE_MODEL')) {
        $value = [Environment]::GetEnvironmentVariable($name, 'User')
        if (-not $value) { $value = [Environment]::GetEnvironmentVariable($name, 'Machine') }
        if (-not $value) { $value = [Environment]::GetEnvironmentVariable($name, 'Process') }
        $result[$name] = $value
    }
    $result | ConvertTo-Json -Compress
    """
    result = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
                            stdin=subprocess.DEVNULL, capture_output=True, check=True, timeout=30)
    values = json.loads(result.stdout.decode("utf-8-sig"))
    names = ("FORGECODE_API_KEY", "FORGECODE_BASE_URL", "FORGECODE_MODEL")
    if not all(isinstance(values.get(name), str) and values[name] for name in names):
        raise RuntimeError("Missing Windows FORGECODE variables")
    for name in names:
        os.environ[name] = values[name]
