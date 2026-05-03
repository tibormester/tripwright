from __future__ import annotations

from .npc_profile import NPCProfile
from .conversation_state import ConversationState    
from .prompts.npc_prompts import *

class PromptBuilder:
    """Assembles npc model prompts from reusable instructions, profile data, and state."""

    def build_prompt(self, state: ConversationState) -> str:
        parts = [
            self._build_prefix(state.npc_profile),
            self._build_conversation_context(state),
            self._build_suffix(state.npc_profile),
        ]
        return "\n".join(part for part in parts if part)
    
    def _build_prefix(self, profile: NPCProfile) -> str:
        """Build the stable instruction block for NPC identity, behavior, and realism constraints."""
        prompt = f"""
        {NPC_SYSTEM_PROMPT_PREFIX}    
        {profile.name}
        {profile.background}
        {profile.role}
        {profile.speaking_style}
        {profile.physical_description}
        {profile.mental_description}
        {profile.emotional_description}
        {profile.local_flavor}
        {profile.beliefs}
        Overt goals: {', '.join(profile.overt_goals)}
        Subtle goals: {', '.join(profile.subtle_goals)}
        {REALISM_CONSTRAINTS}
        {OUTPUT_FORMAT}
        """
        return prompt

    def _build_conversation_context(self, state: ConversationState) -> str:
        """Build the dynamic context block from scene text, state, flags, goals, and dialogue history."""
        return "".join(str(turn) for turn in state.conversation_history)

    def _build_suffix(self, profile: NPCProfile) -> str:
        """Build the instruction block that enforces JSON output with dialogue, thoughts, and flags."""
        prompt = f"""
        {NPC_SYSTEM_PROMPT_SUFFIX}
        Overt goals: {', '.join(profile.overt_goals)}
        Subtle goals: {', '.join(profile.subtle_goals)}
        {REALISM_CONSTRAINTS}
        {OUTPUT_FORMAT}
        {OUTPUT_FORMAT}
        """
        return prompt
    


    
