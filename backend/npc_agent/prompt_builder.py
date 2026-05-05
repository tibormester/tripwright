from __future__ import annotations

from .constants import EXIT_CONVERSATION_TAG
from .conversation_state import ConversationState
from .npc_profile import NPCProfile
from .prompts.npc_prompts import *


def build_prompt(state: ConversationState) -> str:
    """Construct the full prompt for the npc by sandwiching the conversation history between a prefix and suffix prompt."""
    parts = [
        _build_prefix(state.npc_profile),
        _build_runtime_context(state),
        _build_suffix(state.npc_profile),
    ]
    return "\n".join(part for part in parts if part)


def _build_prefix(profile: NPCProfile) -> str:
    """Build the stable instruction block for NPC identity, behavior, and output rules."""
    return f"""
    {NPC_SYSTEM_PROMPT_PREFIX}

    NPC Profile
    Name: {profile.name}
    Background: {profile.background}
    Role: {profile.role}
    Speaking style: {profile.speaking_style}
    Physical description: {profile.physical_description}
    Mental description: {profile.mental_description}
    Emotional description: {profile.emotional_description}
    Local flavor: {profile.local_flavor}
    Beliefs: {profile.beliefs}

    Overt goals
    {_format_goals(profile.overt_goals)}

    Subtle goals
    {_format_goals(profile.subtle_goals)}

    {REALISM_CONSTRAINTS}
    {FLAG_FORMAT_RULES}
    {OUTPUT_FORMAT}
    """


def _build_runtime_context(state: ConversationState) -> str:
    """Build the runtime context block from location, hidden metadata, and visible dialogue history."""
    history = "".join(str(turn) for turn in state.conversation_history)
    hidden_metadata = _format_metadata(state.hidden_metadata)
    return f"""
    Runtime context
    Current location: {state.location}

    Hidden metadata already known
    {hidden_metadata}

    Important rule: tags are one-time machine signals. Do not repeat old tags just because they already exist in hidden metadata.
    Only emit a tag if it is newly earned or newly discovered in this turn.
    Use the narrator setup and earlier conversation as your best clues about the player's state, energy, and what kind of subtle social beat would feel natural.

    Conversation so far
    {history}
    """


def _build_suffix(profile: NPCProfile) -> str:
    """Build the instruction block that reinforces exact goal-tag usage and strict JSON output."""
    return f"""
    {NPC_SYSTEM_PROMPT_SUFFIX}

    Remaining overt goals
    {_format_goals(profile.overt_goals)}

    Remaining subtle goals
    {_format_goals(profile.subtle_goals)}

    Goal completion rule
    - If you complete a goal this turn, emit exactly one tag whose name exactly matches that goal name.
    - Example: if the completed goal name is build_rapport, emit <build_rapport></build_rapport>
    - If the conversation has reached a natural stopping point, you may also emit <{EXIT_CONVERSATION_TAG}>brief hidden reason</{EXIT_CONVERSATION_TAG}>.
    - {EXIT_CONVERSATION_TAG} is always a valid option when the player has what they need, the exchange is stalling, or a short goodbye would feel more human than stretching the scene.

    Metadata rule
    - If you want to store hidden metadata, emit a tag with the value between the opening and closing tags.
    - Example: <coffee_shop>pike's place</coffee_shop>

    Output rule
    - Respond with JSON only.
    - Do not wrap the JSON in markdown.
    - Do not explain the tags.
    - Put all tags in the flags string field.

    {FLAG_FORMAT_RULES}
    {OUTPUT_FORMAT}
    """


def _format_goals(goals: dict[str, str]) -> str:
    if not goals:
        return "- none"

    blocks: list[str] = []
    for goal_name, description in goals.items():
        cleaned_description = description.strip()
        if "\n" not in cleaned_description:
            blocks.append(f"- {goal_name}: {cleaned_description}")
            continue

        indented_description = "\n".join(
            f"  {line}" if line else "" for line in cleaned_description.splitlines()
        )
        blocks.append(f"- {goal_name}:\n{indented_description}")

    return "\n".join(blocks)


def _format_metadata(metadata: dict[str, str]) -> str:
    if not metadata:
        return "- none"
    return "\n".join(f"- {key}: {value or '[present]'}" for key, value in metadata.items())
