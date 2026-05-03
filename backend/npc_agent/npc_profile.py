from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class NPCProfile:
    """Defines the character-specific content used to drive NPC behavior."""

    name: str
    role: str
    speaking_style: str
    physical_traits: list[str] = field(default_factory=list)
    mental_traits: list[str] = field(default_factory=list)
    emotional_traits: list[str] = field(default_factory=list)
    beliefs: list[str] = field(default_factory=list)
    overt_goals: list[str] = field(default_factory=list)
    subtle_goals: list[str] = field(default_factory=list)
    local_flavor: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the NPC profile into a JSON-compatible dictionary."""
        raise NotImplementedError

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NPCProfile":
        """Create an NPC profile from a JSON-compatible dictionary."""
        raise NotImplementedError


class StaticNPCProfileFactory:
    """Creates predefined NPC profiles for early prototyping and testing."""

    def create_hotel_receptionist(self) -> NPCProfile:
        """Build a static hotel receptionist profile for the first prototype."""
        raise NotImplementedError
