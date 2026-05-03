from __future__ import annotations

from .agent import Agent
from .npc_profile import NPCProfile
from .prompt_builder import PromptBuilder
from .state import ConversationState, SceneText


class AgentBuilder:
    """Creates agents and seeds them with the initial conversation context."""

    def create_scene_text(
        self,
        setting: str,
        npc_intro: str,
        first_contact: str,
        transition: str | None = None,
    ) -> SceneText:
        """Create the static narration bundle used to initialize a scene."""
        raise NotImplementedError

    def create_conversation_state(
        self,
        location: str,
        scene_text: SceneText,
        profile: NPCProfile,
    ) -> ConversationState:
        """Create a fresh conversation state for a new NPC interaction."""
        raise NotImplementedError

    def seed_scene_context(self, state: ConversationState) -> None:
        """Inject static narration into the initial dialogue history or runtime context."""
        raise NotImplementedError

    def create_agent(self, prompt_builder: PromptBuilder, model_name: str) -> Agent:
        """Construct the runtime agent with its required dependencies."""
        raise NotImplementedError
