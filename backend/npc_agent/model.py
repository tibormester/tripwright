from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from .conversation_state import DialogueTurn

DEFAULT_MODEL_NAME = "gpt-4o-mini"
TAG_PATTERN = re.compile(r"<([a-zA-Z0-9_]+)>(.*?)</\1>", re.DOTALL)


def _load_env_file() -> None:
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


def call_model(prompt: str) -> DialogueTurn:
    """Call the language model with the given prompt and parse the JSON response."""
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError(
            "The 'openai' package is required to call the NPC model. "
            "Install it with `pip install openai`."
        ) from exc

    _load_env_file()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set.")

    model_name = os.getenv("OPENAI_MODEL", DEFAULT_MODEL_NAME)
    client = OpenAI(api_key=api_key)

    request_kwargs = {
        "model": model_name,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"},
    }

    try:
        response = client.chat.completions.create(**request_kwargs)
    except Exception as exc:
        message = str(exc)
        if "response_format" not in message or "not supported" not in message:
            raise

        request_kwargs.pop("response_format", None)
        response = client.chat.completions.create(**request_kwargs)

    raw_content = response.choices[0].message.content or "{}"
    payload = _parse_model_payload(raw_content)

    return DialogueTurn(
        speaker="NPC",
        dialogue=payload.get("dialogue", ""),
        thinking=payload.get("thinking"),
        flags=payload.get("flags", []),
    )


def extract_tags(flags: str) -> list[tuple[str, str]]:
    """Extract exact XML-like start/end tag pairs and their inner text."""
    if not flags:
        return []
    return [(match.group(1), match.group(2).strip()) for match in TAG_PATTERN.finditer(flags)]


def _parse_model_payload(raw_content: str) -> dict[str, Any]:
    """Parse and normalize the model JSON payload."""
    try:
        payload = json.loads(raw_content)
    except json.JSONDecodeError:
        payload = json.loads(_extract_json_object(raw_content))

    if not isinstance(payload, dict):
        raise ValueError("Model response must decode to a JSON object.")

    dialogue = str(payload.get("dialogue", "")).strip()
    thinking_value = payload.get("thoughts", payload.get("thinking"))
    thinking = str(thinking_value).strip() if thinking_value else None
    raw_flags = _normalize_flags(payload.get("flags"))
    flags = extract_tags(raw_flags)

    return {
        "dialogue": dialogue,
        "thinking": thinking,
        "flags": flags,
    }


def _extract_json_object(raw_content: str) -> str:
    """Extract the first JSON object from a mixed-content model response."""
    start = raw_content.find("{")
    end = raw_content.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("Could not find a JSON object in the model response.")
    return raw_content[start : end + 1]


def _normalize_flags(flags: Any) -> str:
    """Coerce model flags into the raw string format expected from the prompt."""
    if flags is None:
        return ""
    if isinstance(flags, str):
        return flags.strip()
    if isinstance(flags, list):
        return ", ".join(str(flag).strip() for flag in flags if str(flag).strip())
    return str(flags).strip()
