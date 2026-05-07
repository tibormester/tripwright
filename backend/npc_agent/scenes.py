from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from .npc_profile import NPCProfile


@dataclass(frozen=True)
class SceneDefinition:
    """Fallback static configuration for a location the player can travel to next."""

    location_id: str
    label: str
    description: str
    location: str
    narrator_text: str
    npc_factory: Callable[[], NPCProfile]


# Static fallback scene data used when dynamic world generation is unavailable.
HOTEL_LOBBY_SCENE = SceneDefinition(
    location_id="hotel_lobby",
    label="Hotel Lobby",
    description="Check in with Love Patel at the front desk and get oriented after your flight.",
    location="the lobby of a grand city hotel",
    narrator_text=(
        "After a sleepless red-eye, you step into the hotel lobby with your carry-on still in hand. "
        "The room is all warm light, polished stone, and low conversation, and the front desk ahead of you "
        "feels like the first real pause since you left the airport. Behind it stands Love Patel, alert and "
        "welcoming, already looking up as you arrive."
    ),
    npc_factory=NPCProfile.love_patel,
)


TRAVEL_DESTINATIONS: tuple[SceneDefinition, ...] = (
    SceneDefinition(
        location_id="coffee_shop",
        label="Corner Coffee",
        description="Head to a cozy coffee shop nearby and meet Kat, the quirky barista.",
        location="a cozy neighborhood coffee shop a few blocks from the hotel",
        narrator_text=(
            "A short walk from the hotel, the street opens onto a compact coffee shop with fogged windows, "
            "a handwritten specials board, and the smell of espresso drifting out every time the door swings open. "
            "Inside, cups clink, the grinder growls, and behind the counter stands Kat, a barista with a lively half-smile "
            "and the kind of energy that makes the room feel a little less tired."
        ),
        npc_factory=NPCProfile.kat_barista,
    ),
    SceneDefinition(
        location_id="riverside_walk",
        label="Riverside Walk",
        description="Take a breather along the river and check in with Rae at the promenade kiosk.",
        location="the riverside promenade a short walk from downtown",
        narrator_text=(
            "The city opens up as the streets slope toward the river, where the air feels cooler and the sound of traffic thins into gulls, water, and distant conversation. "
            "Near the promenade entrance, a small kiosk sits beside a rack of maps and paper cups of ice water. Rae Moreno looks up from the counter with the unhurried ease of someone who knows this stretch of river by heart."
        ),
        npc_factory=NPCProfile.rae_riverside_guide,
    ),
    SceneDefinition(
        location_id="bookstore_lounge",
        label="Bookstore Lounge",
        description="Duck into a quiet bookstore lounge and meet Eli among the shelves.",
        location="a narrow independent bookstore with a quiet upstairs lounge",
        narrator_text=(
            "A bell gives a soft, tired ring as you step into the bookstore, where tall shelves narrow the room into calm little corridors of paper, lamp light, and dust-warm wood. "
            "Somewhere upstairs, a chair scrapes gently against the floorboards. On the main level, Eli Navarro glances up from a returns cart with a thoughtful expression that suggests they already know how to make the place feel quieter."
        ),
        npc_factory=NPCProfile.eli_bookstore_clerk,
    ),
)


def get_initial_scene() -> SceneDefinition:
    return HOTEL_LOBBY_SCENE


def build_travel_options() -> list[dict[str, str]]:
    return [
        {
            "location_id": destination.location_id,
            "label": destination.label,
            "description": destination.description,
        }
        for destination in TRAVEL_DESTINATIONS
    ]


def get_destination_by_choice(choice_index: int) -> SceneDefinition | None:
    if choice_index < 0 or choice_index >= len(TRAVEL_DESTINATIONS):
        return None
    return TRAVEL_DESTINATIONS[choice_index]
