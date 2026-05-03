from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.npc_agent.npc_profile import NPCProfile

from .prompt_builder import PromptBuilder
from .conversation_state import ConversationState, DialogueTurn



class Agent:
    """Executes one NPC turn using profile data, state, and prompt assembly logic."""

    def __init__(self, prompt_builder: PromptBuilder, model_name: str) -> None:
        """Store the dependencies required to run the NPC agent."""
        raise NotImplementedError

    def initialize_conversation(self, npc_profile: NPCProfile, location: str) -> ConversationState:
        """Set up the initial conversation state with the NPC profile and starting location."""
        raise NotImplementedError

    def run_turn(self, state: ConversationState, user_input: str) -> DialogueTurn:
        """Process one user input, call the model, update state, and return the NPC turn result."""
        state.conversation_history.append(DialogueTurn(speaker="User", dialogue=user_input))

        turn = self._call_model(self.prompt_builder.build_prompt(state)) 
        self._process_goal_flags(turn.flags, state.npc_profile)

        # check if the convo is over, and if so change the text to reflect that
        if self._check_conversation_end(state.npc_profile):
            turn = self.finish_conversation(state)
        
        # append to history and return update to client
        state.conversation_history.append(turn)
        return turn

    def finish_conversation(self, state: ConversationState) -> DialogueTurn:
        """Perform any cleanup or finalization when the conversation is complete."""
        raise NotImplementedError

    def _call_model(self, prompt: str) -> DialogueTurn:
        """Call the language model with the given prompt and return the raw response."""
        """TODO: make this call the openai api using the env api key,  then parse the response into the DialogueTurn object"""
        raise NotImplementedError

    def _process_goal_flags(self, flags: str, npc_profile: NPCProfile) -> None:
        """given a string containing potential goal flags, update the npc profile"""
        raise NotImplementedError
    
    def _check_conversation_end(self, npc_profile: NPCProfile) -> bool:
        """check if all goals have been achieved and the conversation should end"""
        return not npc_profile.overt_goals and not npc_profile.subtle_goals
"""
when the goals are met, then the npc model response will emit a flag declaring it

this agent class will look for the flag, then update the npc profile to remove that goal, so that in future conversation turns, it doesn't appear

if all goals have been achieved then we finish the conversation.

TODO: 1. update the npc prompts to better explain flags and goals
TODO: 2. update the love_patel prompts to be better

TODO: 0. implement the agent class to do the above

"""