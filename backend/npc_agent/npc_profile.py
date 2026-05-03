from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class NPCProfile:
    """Maintains the character-specific content used to drive NPC behavior."""

    name: str
    background: str
    role: str
    speaking_style: str
    physical_description: str
    mental_description: str
    emotional_description: str
    local_flavor: str
    beliefs: str
    overt_goals: dict[str, str] = field(default_factory=dict)
    subtle_goals: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the NPC profile into a JSON-compatible dictionary."""
        return {
            "name": self.name,
            "background": self.background,
            "role": self.role,
            "speaking_style": self.speaking_style,
            "physical_description": self.physical_description,
            "mental_description": self.mental_description,
            "emotional_description": self.emotional_description,
            "local_flavor": self.local_flavor,
            "beliefs": self.beliefs,
            "overt_goals": self.overt_goals,
            "subtle_goals": self.subtle_goals,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NPCProfile":
        """Create an NPC profile from a JSON-compatible dictionary."""
        return cls(
            name=data.get("name", ""),
            background=data.get("background", ""),
            role=data.get("role", ""),
            speaking_style=data.get("speaking_style", ""),
            physical_description=data.get("physical_description", ""),
            mental_description=data.get("mental_description", ""),
            emotional_description=data.get("emotional_description", ""),
            local_flavor=data.get("local_flavor", ""),
            beliefs=data.get("beliefs", ""),
            overt_goals=_normalize_goals(data.get("overt_goals", {})),
            subtle_goals=_normalize_goals(data.get("subtle_goals", {})),
        )


from .prompts.love_patel import (
    BACKGROUND,
    BELIEFS,
    EMOTIONAL_DESCRIPTION,
    LOCAL_FLAVOR,
    MENTAL_DESCRIPTION,
    NAME,
    OVERT_GOALS,
    PHYSICAL_DESCRIPTION,
    ROLE,
    SPEAKING_STYLE,
    SUBTLE_GOALS,
)


class StaticNPCProfileFactory:
    """Creates predefined NPC profiles for early prototyping and testing."""

    def create_hotel_receptionist(self) -> NPCProfile:
        return NPCProfile(
            name=NAME,
            background=BACKGROUND,
            role=ROLE,
            speaking_style=SPEAKING_STYLE,
            physical_description=PHYSICAL_DESCRIPTION,
            mental_description=MENTAL_DESCRIPTION,
            emotional_description=EMOTIONAL_DESCRIPTION,
            local_flavor=LOCAL_FLAVOR,
            beliefs=BELIEFS,
            overt_goals=OVERT_GOALS,
            subtle_goals=SUBTLE_GOALS,
        )


def _normalize_goals(raw_goals: Any) -> dict[str, str]:
    """Allow goal dictionaries directly while tolerating older list-based data."""
    if isinstance(raw_goals, dict):
        return {str(key): str(value) for key, value in raw_goals.items()}

    if isinstance(raw_goals, list):
        goals: dict[str, str] = {}
        for goal in raw_goals:
            description = str(goal)
            goal_name = _slugify(description)
            goals[goal_name] = description
        return goals

    return {}


def _slugify(value: str) -> str:
    return "_".join("".join(ch.lower() if ch.isalnum() else " " for ch in value).split())
