from __future__ import annotations

from .npc_profile import NPCProfile
from .conversation_state import ConversationState    
from .prompts.npc_prompts import *

class PromptBuilder:
    """Assembles npc model prompts from reusable instructions, profile data, and state."""

    @staticmethod
    def build_prompt(state: ConversationState) -> str:
        """Constructs the full prompt for the npc by sandwiching the conversation history between a prefix and suffic prompt."""
        parts = [
            PromptBuilder._build_prefix(state.npc_profile),
            PromptBuilder._build_conversation_context(state),
            PromptBuilder._build_suffix(state.npc_profile),
        ]
        return "\n".join(part for part in parts if part)
    
    @staticmethod
    def _build_prefix(profile: NPCProfile) -> str:
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

    @staticmethod
    def _build_conversation_context(state: ConversationState) -> str:
        """Build the dynamic context block from scene text, state, flags, goals, and dialogue history."""
        return "".join(str(turn) for turn in state.conversation_history)

    @staticmethod
    def _build_suffix(profile: NPCProfile) -> str:
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
    


    
