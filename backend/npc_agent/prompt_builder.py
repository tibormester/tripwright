from __future__ import annotations

from dataclasses import dataclass

from .npc_profile import NPCProfile
from .state import ConversationState


@dataclass
class PromptPackage:
    """Holds the assembled prompt content that will be sent to the model."""

    system_prompt: str
    user_prompt: str


class PromptBuilder:
    """Assembles model prompts from reusable instructions, profile data, and state."""

    def build_system_prompt(self, profile: NPCProfile) -> str:
        """Build the stable instruction block for NPC identity, behavior, and realism constraints."""
        raise NotImplementedError

    def build_runtime_context(self, state: ConversationState) -> str:
        """Build the dynamic context block from scene text, state, flags, goals, and dialogue history."""
        raise NotImplementedError

    def build_output_contract(self) -> str:
        """Build the instruction block that enforces JSON output with dialogue, thoughts, and flags."""
        raise NotImplementedError

    def build_prompt_package(self, profile: NPCProfile, state: ConversationState) -> PromptPackage:
        """Assemble the final prompt package from profile content and runtime conversation state."""
        raise NotImplementedError
