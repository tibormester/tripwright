from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .prompt_builder import PromptBuilder
from .state import ConversationState


@dataclass
class AgentTurnResult:
    """Represents the parsed result of a single NPC model turn."""

    dialogue: str
    thoughts: str
    flags: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "dialogue": self.dialogue,
            "thoughts": self.thoughts,
            "flags": self.flags,
        }


class Agent:
    """Executes one NPC turn using profile data, state, and prompt assembly logic."""

    def __init__(self, prompt_builder: PromptBuilder, model_name: str) -> None:
        """Store the dependencies required to run the NPC agent."""
        raise NotImplementedError

    def run_turn(self, state: ConversationState, user_input: str) -> AgentTurnResult:
        """Process one user input, call the model, update state, and return the NPC turn result."""
        raise NotImplementedError
