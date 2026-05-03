from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DialogueTurn:
    """Represents one visible turn in the conversation history."""

    speaker: str
    text: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize a dialogue turn into a JSON-compatible dictionary."""
        raise NotImplementedError

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DialogueTurn":
        """Create a dialogue turn from a JSON-compatible dictionary."""
        raise NotImplementedError


@dataclass
class SceneText:
    """Holds the static narration used to establish the scene."""

    setting: str
    npc_intro: str
    first_contact: str
    transition: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize the scene text into a JSON-compatible dictionary."""
        raise NotImplementedError

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SceneText":
        """Create scene text from a JSON-compatible dictionary."""
        raise NotImplementedError


@dataclass
class ConversationState:
    """Stores all mutable, JSON-serializable state for one NPC conversation."""

    location: str
    scene_text: SceneText
    npc_profile: dict[str, Any]
    dialogue_history: list[DialogueTurn] = field(default_factory=list)
    active_flags: list[str] = field(default_factory=list)
    completed_goals: list[str] = field(default_factory=list)
    turn_count: int = 0

    def append_turn(self, speaker: str, text: str) -> None:
        """Append a new dialogue turn to the conversation history."""
        raise NotImplementedError

    def record_flags(self, flags: list[str]) -> None:
        """Store newly raised flags for the current conversation state."""
        raise NotImplementedError

    def mark_completed_goals(self, goals: list[str]) -> None:
        """Record overt or subtle goals that have been completed."""
        raise NotImplementedError

    def increment_turn_count(self) -> None:
        """Advance the tracked turn counter for the conversation."""
        raise NotImplementedError

    def to_dict(self) -> dict[str, Any]:
        """Serialize the full conversation state into a JSON-compatible dictionary."""
        raise NotImplementedError

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConversationState":
        """Rebuild conversation state from a JSON-compatible dictionary."""
        raise NotImplementedError
