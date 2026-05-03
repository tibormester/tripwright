from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .npc_profile import NPCProfile


@dataclass
class DialogueTurn:
    """Represents one visible turn in the conversation history."""

    speaker: str  # Narrator, NPC Name, User Name
    dialogue: str  # their dialogue text
    thinking: str | None = None  # internal thoughts - narrator and npc only
    flags: list[tuple[str, str]] = field(default_factory=list)  # parsed one-time hidden tags

    def to_dict(self) -> dict[str, Any]:
        """Serialize a dialogue turn into a JSON-compatible dictionary."""
        output = {
            "speaker": self.speaker,
            "dialogue": self.dialogue,
        }
        if self.thinking:
            output["thinking"] = self.thinking
        if self.flags:
            output["flags"] = [[tag_name, tag_value] for tag_name, tag_value in self.flags]
        return output

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DialogueTurn:
        raw_flags = data.get("flags", [])
        flags: list[tuple[str, str]] = []

        if isinstance(raw_flags, list):
            for item in raw_flags:
                if isinstance(item, (list, tuple)) and len(item) == 2:
                    flags.append((str(item[0]), str(item[1])))
                elif isinstance(item, dict):
                    flags.append((str(item.get("tag", "")), str(item.get("value", ""))))

        return cls(
            speaker=data.get("speaker", ""),
            dialogue=data.get("dialogue", ""),
            thinking=data.get("thinking"),
            flags=flags,
        )

    def __str__(self) -> str:
        """Format the dialogue turn for display in the conversation history."""
        output = f"{self.speaker}: {self.dialogue}\n"
        if self.thinking:
            output += f"(internally thinking: {self.thinking})\n"
        return output


@dataclass
class ConversationState:
    """Stores all mutable, JSON-serializable state for one NPC conversation."""

    location: str
    npc_profile: NPCProfile
    conversation_history: list[DialogueTurn] = field(default_factory=list)
    hidden_metadata: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the full conversation state into a JSON-compatible dictionary."""
        return {
            "location": self.location,
            "npc_profile": self.npc_profile.to_dict(),
            "conversation_history": [turn.to_dict() for turn in self.conversation_history],
            "hidden_metadata": self.hidden_metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ConversationState:
        """Rebuild conversation state from a JSON-compatible dictionary."""
        return cls(
            location=data.get("location", ""),
            npc_profile=NPCProfile.from_dict(data.get("npc_profile", {})),
            conversation_history=[DialogueTurn.from_dict(turn) for turn in data.get("conversation_history", [])],
            hidden_metadata={
                str(key): str(value) for key, value in data.get("hidden_metadata", {}).items()
            },
        )
