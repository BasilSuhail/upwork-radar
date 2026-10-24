"""Text in, text out through the `claude` CLI (the owner's Claude subscription, no API key)."""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time

TIMEOUT = 180
RETRIES = 3


def ask(system: str, prompt: str, model: str = "haiku") -> str:
    exe = shutil.which("claude") or os.path.expanduser("~/.local/bin/claude")
    cmd = [
        exe, "-p",
        "--safe-mode",               # ignore the user's CLAUDE.md, skills, hooks, plugins
        "--model", model,
        "--tools", "",
        "--strict-mcp-config",
        "--no-session-persistence",
        "--output-format", "text",
        "--system-prompt", system,
    ]
    env = os.environ.copy()
    env.pop("CLAUDECODE", None)
    env.pop("CLAUDE_CODE_ENTRYPOINT", None)
    cwd = tempfile.mkdtemp(prefix="upwork-radar-")   # neutral dir: no project CLAUDE.md
    err = ""
    for attempt in range(RETRIES):
        proc = subprocess.run(cmd, input=prompt, capture_output=True, text=True,
                              env=env, cwd=cwd, timeout=TIMEOUT)
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip()
        err = (proc.stderr or proc.stdout).strip()[:300]
        time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"claude CLI failed: {err}")
