from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

@dataclass
class NPCProfile:
    """Maintains the character-specific content used to drive NPC behavior."""

    # core personality stuff, technically still fluff
    name: str
    background: str
    role: str

    # personality stuff, just for fluff
    speaking_style: str
    physical_description: str
    mental_description: str
    emotional_description: str
    local_flavor: str
    beliefs: str

    # agent success criteria - used for evaluation and to help guide the agent
    overt_goals: list[str] = field(default_factory=list)
    subtle_goals: list[str] = field(default_factory=list)
    

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
            overt_goals=data.get("overt_goals", []),
            subtle_goals=data.get("subtle_goals", []),
        )



from .prompts.love_patel import NAME, BACKGROUND, ROLE, SPEAKING_STYLE, PHYSICAL_DESCRIPTION, MENTAL_DESCRIPTION, EMOTIONAL_DESCRIPTION, LOCAL_FLAVOR, BELIEFS, OVERT_GOALS, SUBTLE_GOALS
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
            subtle_goals=SUBTLE_GOALS
        )