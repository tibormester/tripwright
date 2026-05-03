from __future__ import annotations

from backend.npc_agent.npc_profile import NPCProfile

from .conversation_state import ConversationState, DialogueTurn
from .model import call_model
from .prompt_builder import build_prompt


def initialize_conversation(npc_profile: NPCProfile, location: str) -> ConversationState:
    """Set up the initial conversation state with the NPC profile and starting location."""
    state = ConversationState(location=location, npc_profile=npc_profile)
    if location:
        state.conversation_history.append(
            DialogueTurn(
                speaker="Narrator",
                dialogue=f"A jet lagged traveler arrives at {location}, blinking his eyes wearily as he enters.",
            )
        )
    return state


def run_turn(state: ConversationState, user_input: str) -> ConversationState:
    """Process one user input, call the model, update state, and return the updated state."""
    state.conversation_history.append(DialogueTurn(speaker="User", dialogue=user_input))

    turn = call_model(build_prompt(state))
    turn.speaker = state.npc_profile.name or turn.speaker

    if turn.flags:
        _process_flags(turn.flags, state)
        turn.flags = []

    if _check_conversation_end(state.npc_profile):
        turn = _finish_conversation(state)
        if turn.flags:
            _process_flags(turn.flags, state)
            turn.flags = []

    state.conversation_history.append(turn)
    return state


def _finish_conversation(state: ConversationState) -> DialogueTurn:
    """Perform any cleanup or finalization when the conversation is complete."""
    return DialogueTurn(
        speaker=state.npc_profile.name,
        dialogue="I believe we've covered everything I needed to help with. If you'd like anything else, I'm still here.",
        thinking="All current overt and subtle goals have been completed.",
        flags=[("conversation_end", "")],
    )


def _process_flags(flags: list[tuple[str, str]], state: ConversationState) -> None:
    """Store tag values and remove matching completed goals."""
    for tag_name, tag_value in flags:
        state.hidden_metadata[tag_name] = tag_value
        state.npc_profile.overt_goals.pop(tag_name, None)
        state.npc_profile.subtle_goals.pop(tag_name, None)


def _check_conversation_end(npc_profile: NPCProfile) -> bool:
    """Check if all goals have been achieved and the conversation should end."""
    return not npc_profile.overt_goals and not npc_profile.subtle_goals
