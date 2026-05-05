from __future__ import annotations

import os
from pathlib import Path


def load_env_file() -> None:
    """Load environment variables from a nearby .env file if present."""
    if os.getenv("OPENAI_API_KEY"):
        return

    candidates = [
        Path.cwd() / ".env",
        Path(__file__).resolve().parents[2] / ".env",
    ]

    for env_path in candidates:
        if not env_path.is_file():
            continue

        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key:
                os.environ.setdefault(key, value)

        if os.getenv("OPENAI_API_KEY"):
            return
