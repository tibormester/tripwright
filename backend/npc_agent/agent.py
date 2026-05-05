from __future__ import annotations

from .constants import EXIT_CONVERSATION_TAG
from .conversation_state import ConversationState, DialogueTurn
from .model import call_model
from .npc_profile import NPCProfile
from .prompt_builder import build_prompt
from .prompts.defaults import (
    build_default_scene_intro,
    build_system_error,
    build_travel_command_usage,
    build_travel_selection_message,
    is_travel_selection_location,
    mark_travel_selection_location,
)
from .scenes import SceneDefinition, build_travel_options, get_destination_by_choice


TRAVEL_OPTIONS = build_travel_options()


def initialize_conversation(
    npc_profile: NPCProfile,
    location: str,
    narrator_text: str | None = None,
) -> ConversationState:
    """Set up the initial conversation state with the NPC profile and opening narration."""
    state = ConversationState(location=location, npc_profile=npc_profile)
    intro = (narrator_text or build_default_scene_intro(location)).strip()
    if intro:
        _append_turn(state, speaker="Narrator", dialogue=intro)
    return state


def start_conversation(state: ConversationState) -> ConversationState:
    """Let the NPC take the opening turn before any user input."""
    _append_npc_turn(state)
    return state


def run_turn(state: ConversationState, user_input: str) -> ConversationState:
    """Process one user input, update state, and return the updated conversation."""
    cleaned_input = user_input.strip()

    if is_travel_selection_location(state.location):
        return _handle_travel_command(state, cleaned_input)

    if cleaned_input:
        _append_turn(state, speaker="User", dialogue=cleaned_input)

    _append_npc_turn(state)
    return state


def _append_npc_turn(state: ConversationState) -> None:
    """Generate, store, and post-process one NPC response."""
    turn = call_model(build_prompt(state))
    turn.speaker = state.npc_profile.name or turn.speaker

    finish_requested = False
    if turn.flags:
        finish_requested = _process_flags(turn.flags, state)
        turn.flags = []

    state.conversation_history.append(turn)

    if finish_requested or _check_conversation_end(state.npc_profile):
        _finish_conversation(state)


def _handle_travel_command(state: ConversationState, command_input: str) -> ConversationState:
    """Accept only numbered /command input while waiting for the next scene selection."""
    _append_turn(state, speaker="User", dialogue=command_input)

    choice_index, error_message = _parse_travel_command(command_input)
    if error_message:
        _append_system_turn(state, error_message)
        return state

    destination = get_destination_by_choice(choice_index)
    if destination is None:
        _append_system_turn(state, f"That destination does not exist. {build_travel_command_usage(len(TRAVEL_OPTIONS))}")
        return state

    return _start_scene(destination)


def _parse_travel_command(command_input: str) -> tuple[int | None, str | None]:
    usage = build_travel_command_usage(len(TRAVEL_OPTIONS))

    if not command_input.startswith("/command"):
        return None, f"A location choice is required right now. {usage}"

    parts = command_input.split(maxsplit=1)
    if len(parts) < 2:
        return None, f"Missing destination number. {usage}"

    choice_text = parts[1].strip().split()[0]
    if not choice_text.isdigit():
        return None, f"Invalid destination number. {usage}"

    choice_index = int(choice_text) - 1
    if get_destination_by_choice(choice_index) is None:
        return None, f"That destination does not exist. {usage}"

    return choice_index, None


def _finish_conversation(state: ConversationState) -> None:
    """Mark the current scene complete and append the next-location prompt."""
    if is_travel_selection_location(state.location):
        return

    state.npc_profile.overt_goals.clear()
    state.npc_profile.subtle_goals.clear()
    state.location = mark_travel_selection_location(state.location)
    _append_turn(state, speaker="System", dialogue=build_travel_selection_message(TRAVEL_OPTIONS))


def _append_turn(state: ConversationState, *, speaker: str, dialogue: str) -> None:
    state.conversation_history.append(DialogueTurn(speaker=speaker, dialogue=dialogue))


def _append_system_turn(state: ConversationState, message: str) -> None:
    _append_turn(state, speaker="System", dialogue=build_system_error(message))


def _start_scene(scene: SceneDefinition) -> ConversationState:
    next_state = initialize_conversation(
        npc_profile=scene.npc_factory(),
        location=scene.location,
        narrator_text=scene.narrator_text,
    )
    return start_conversation(next_state)


def _process_flags(flags: list[tuple[str, str]], state: ConversationState) -> bool:
    """Store tag values, remove matching completed goals, and allow an explicit scene exit signal."""
    finish_requested = False

    for tag_name, tag_value in flags:
        if tag_name == EXIT_CONVERSATION_TAG:
            finish_requested = True
            continue

        state.hidden_metadata[tag_name] = tag_value
        state.npc_profile.overt_goals.pop(tag_name, None)
        state.npc_profile.subtle_goals.pop(tag_name, None)

    return finish_requested


def _check_conversation_end(npc_profile: NPCProfile) -> bool:
    """Check if all goals have been achieved and the conversation should end."""
    return not npc_profile.overt_goals and not npc_profile.subtle_goals
