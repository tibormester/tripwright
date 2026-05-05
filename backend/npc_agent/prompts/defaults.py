from __future__ import annotations

from collections.abc import Sequence
from typing import Mapping

TRAVEL_SELECTION_SUFFIX = " [travel-selection]"
SYSTEM_ERROR_PREFIX = "System error:"

DEFAULT_SCENE_INTRO = (
    "After a sleepless red-eye, you step into the hotel lobby with your carry-on still in hand. "
    "The room is all warm light, polished stone, and low conversation, and the front desk ahead of you "
    "feels like the first real pause since you left the airport. Behind it stands Love Patel, alert and "
    "welcoming, already looking up as you arrive."
)


def build_default_scene_intro(location: str) -> str:
    if not location:
        return DEFAULT_SCENE_INTRO
    return (
        "After a draining red-eye flight, the traveler arrives at "
        f"{location}. The lobby's warm light and polished calm offer a sharp contrast to the "
        "blur of transit, and the front desk feels like the first solid step toward finally getting settled."
    )


def is_travel_selection_location(location: str) -> bool:
    return bool(location) and location.endswith(TRAVEL_SELECTION_SUFFIX)


def mark_travel_selection_location(location: str) -> str:
    if is_travel_selection_location(location):
        base_location = location[: -len(TRAVEL_SELECTION_SUFFIX)]
    else:
        base_location = location
    return f"{base_location.rstrip()}{TRAVEL_SELECTION_SUFFIX}"


def build_travel_selection_message(options: Sequence[Mapping[str, str]]) -> str:
    options_text = "\n".join(
        f"/command {index} - {option['label']}: {option['description']}"
        for index, option in enumerate(options, start=1)
    )
    return (
        "Scene complete. Choose where to go next with one of these commands:\n"
        f"{options_text}"
    )


def build_travel_command_usage(option_count: int) -> str:
    commands = [f"/command {index}" for index in range(1, option_count + 1)]
    if not commands:
        return "No destinations are currently available."
    if len(commands) == 1:
        return f"Use {commands[0]}."
    return f"Use {', '.join(commands[:-1])}, or {commands[-1]}."


def build_system_error(message: str) -> str:
    return f"{SYSTEM_ERROR_PREFIX} {message}"
