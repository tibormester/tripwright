from __future__ import annotations

from backend.npc_agent.npc_profile import NPCProfile

from .conversation_state import ConversationState, DialogueTurn
from .model import call_model
from .prompt_builder import build_prompt

DEFAULT_SCENE_INTRO = (
    "After a draining red-eye flight, the traveler pushes through the revolving doors into "
    "the warm light of the hotel lobby. Suitcase wheels rattle softly over polished floors, "
    "and the front desk comes into view: a calm island of order at the edge of a long, blurry journey."
)


def initialize_conversation(
    npc_profile: NPCProfile,
    location: str,
    narrator_text: str | None = None,
) -> ConversationState:
    """Set up the initial conversation state with the NPC profile and opening narration."""
    state = ConversationState(location=location, npc_profile=npc_profile)
    intro = (narrator_text or _build_default_narrator_text(location)).strip()
    if intro:
        state.conversation_history.append(DialogueTurn(speaker="Narrator", dialogue=intro))
    return state


def start_conversation(state: ConversationState) -> ConversationState:
    """Let the NPC take the opening turn before any user input."""
    state.conversation_history.append(_generate_npc_turn(state))
    return state


def run_turn(state: ConversationState, user_input: str) -> ConversationState:
    """Process one user input, call the model, update state, and return the updated state."""
    cleaned_input = user_input.strip()
    if cleaned_input:
        state.conversation_history.append(DialogueTurn(speaker="User", dialogue=cleaned_input))

    state.conversation_history.append(_generate_npc_turn(state))
    return state


def _generate_npc_turn(state: ConversationState) -> DialogueTurn:
    """Generate one NPC response from the current conversation state."""
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

    return turn


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


def _build_default_narrator_text(location: str) -> str:
    if not location:
        return DEFAULT_SCENE_INTRO
    return (
        "After a draining red-eye flight, the traveler arrives at "
        f"{location}. The lobby's warm light and polished calm offer a sharp contrast to the "
        "blur of transit, and the front desk feels like the first solid step toward finally getting settled."
    )
