"""Core structures for the NPC conversation prototype."""

from .agent import Agent, AgentTurnResult
from .npc_profile import NPCProfile, StaticNPCProfileFactory
from .prompt_builder import PromptBuilder
from .state import ConversationState, DialogueTurn

__all__ = [
    "Agent",
    "AgentTurnResult",
    "ConversationState",
    "DialogueTurn",
    "NPCProfile",
    "PromptBuilder",
    "StaticNPCProfileFactory",
]
