from __future__ import annotations

from dataclasses import dataclass

from .npc_profile import NPCProfile
from .state import ConversationState
from .prompts.npc_prompts import OUTPUT_FORMAT, REALISM_CONSTRAINTS

class PromptBuilder:
    """Assembles npc model prompts from reusable instructions, profile data, and state."""

    def build_prompt(self, state: ConversationState) -> str:
        output = ""
        output.append(self._build_prefix(state.npc_profile))
        output.append(self._build_conversation_context(state))
        output.append(self._build_suffix(state.npc_profile))
        return output
    
    def _build_prefix(self, profile: NPCProfile) -> str:
        """Build the stable instruction block for NPC identity, behavior, and realism constraints."""
        raise NotImplementedError

    def _build_conversation_context(self, state: ConversationState) -> str:
        """Build the dynamic context block from scene text, state, flags, goals, and dialogue history."""
        raise NotImplementedError

    def _build_suffix(self, profile: NPCProfile) -> str:
        """Build the instruction block that enforces JSON output with dialogue, thoughts, and flags."""
        raise NotImplementedError
    


    
