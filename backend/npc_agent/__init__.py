"""Core structures for the NPC conversation prototype."""

from .agent import Agent, AgentTurnResult
from .agent_builder import AgentBuilder
from .npc_profile import NPCProfile, StaticNPCProfileFactory
from .prompt_builder import PromptBuilder, PromptPackage
from .state import ConversationState, DialogueTurn, SceneText

__all__ = [
    "Agent",
    "AgentBuilder",
    "AgentTurnResult",
    "ConversationState",
    "DialogueTurn",
    "NPCProfile",
    "PromptBuilder",
    "PromptPackage",
    "SceneText",
    "StaticNPCProfileFactory",
]
