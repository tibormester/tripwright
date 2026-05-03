from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .npc_profile import NPCProfile
from .prompt_builder import PromptBuilder, PromptPackage
from .state import ConversationState


@dataclass
class AgentTurnResult:
    """Represents the parsed result of a single NPC model turn."""

    dialogue: str
    thoughts: str
    flags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the turn result into a JSON-compatible dictionary."""
        raise NotImplementedError


class Agent:
    """Executes one NPC turn using profile data, state, and prompt assembly logic."""

    def __init__(self, prompt_builder: PromptBuilder, model_name: str) -> None:
        """Store the dependencies required to run the NPC agent."""
        raise NotImplementedError

    def run_turn(self, state: ConversationState, profile: NPCProfile, user_input: str) -> AgentTurnResult:
        """Process one user input, call the model, update state, and return the NPC turn result."""
        raise NotImplementedError

    def build_prompt(self, state: ConversationState, profile: NPCProfile) -> PromptPackage:
        """Create the prompt package for the current conversation turn."""
        raise NotImplementedError

    def parse_response(self, response_text: str) -> AgentTurnResult:
        """Parse raw model output into normalized dialogue, thoughts, and flags."""
        raise NotImplementedError

    def apply_turn_result(self, state: ConversationState, result: AgentTurnResult) -> None:
        """Apply parsed turn output back onto the mutable conversation state."""
        raise NotImplementedError
