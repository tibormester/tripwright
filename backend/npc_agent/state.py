from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .npc_profile import NPCProfile

@dataclass
class DialogueTurn:
    """
    Represents one visible turn in the conversation history.
    
    """

    speaker: str #Narrator, NPC Name, User Name
    dialogue: str #their dialogue text
    thinking: str | None #their internal thoughts - narrator and npc only
    flags: str | None #any flags associated with this turn - npc only

    def to_dict(self) -> dict[str, Any]:
        """Serialize a dialogue turn into a JSON-compatible dictionary."""
        raise NotImplementedError

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DialogueTurn:
        """Create a dialogue turn from a JSON-compatible dictionary."""
        raise NotImplementedError


@dataclass
class ConversationState:
    """Stores all mutable, JSON-serializable state for one NPC conversation."""

    location: str
    npc_profile: NPCProfile
    conversation_history: list[DialogueTurn] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the full conversation state into a JSON-compatible dictionary."""
        raise NotImplementedError

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ConversationState:
        """Rebuild conversation state from a JSON-compatible dictionary."""
        raise NotImplementedError
