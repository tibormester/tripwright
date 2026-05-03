from __future__ import annotations

import logging

from flask import Flask, jsonify, request

from npc_agent.agent import initialize_conversation, run_turn, start_conversation
from npc_agent.conversation_state import ConversationState, DialogueTurn
from npc_agent.npc_profile import NPCProfile

app = Flask(__name__)

if not app.logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
app.logger.setLevel(logging.INFO)

DEFAULT_LOCATION = "the lobby of a grand city hotel"
DEFAULT_SCENE_INTRO = (
    "After a sleepless red-eye, you step into the hotel lobby with your carry-on still in hand. "
    "The room is all warm light, polished stone, and low conversation, and the front desk ahead of you "
    "feels like the first real pause since you left the airport. Behind it stands Love Patel, alert and "
    "welcoming, already looking up as you arrive."
)


def _find_last_turn(turns: list[DialogueTurn], *, speaker: str) -> DialogueTurn | None:
    for turn in reversed(turns):
        if turn.speaker == speaker:
            return turn
    return None


def _extract_new_flags(
    previous_hidden_metadata: dict[str, str],
    current_hidden_metadata: dict[str, str],
) -> dict[str, str]:
    return {
        key: value
        for key, value in current_hidden_metadata.items()
        if previous_hidden_metadata.get(key) != value
    }

def _format_inline(value: str | None) -> str:
    if not value:
        return '""'
    return f'"{value.replace(chr(10), "\\n").replace(chr(13), "\\r")}"'


def _format_flags(flags: dict[str, str]) -> str:
    if not flags:
        return '""'
    return "\n".join(f"  - {tag}: {_format_inline(value)}" for tag, value in flags.items())


def _format_goals(goals: dict[str, str]) -> str:
    if not goals:
        return '""'
    return "\n".join(f"  - {goal}: {_format_inline(description)}" for goal, description in goals.items())


def _log_conversation_state(
    *,
    action: str,
    state: ConversationState,
    previous_hidden_metadata: dict[str, str] | None = None,
) -> None:
    previous_hidden_metadata = previous_hidden_metadata or {}
    user_turn = _find_last_turn(state.conversation_history, speaker="User")
    npc_name = state.npc_profile.name or "NPC"
    npc_turn = _find_last_turn(state.conversation_history, speaker=npc_name)
    new_flags = _extract_new_flags(previous_hidden_metadata, state.hidden_metadata)

    log_message = "\n".join(
        [
            f"[{action}] {request.method} {request.path}",
            f"user: {_format_inline(user_turn.dialogue if user_turn else None)}",
            f"npc dialogue: {_format_inline(npc_turn.dialogue if npc_turn else None)}",
            f"npc thinking: {_format_inline(npc_turn.thinking if npc_turn else None)}",
            "flags:",
            _format_flags(new_flags),
            "remaining overt goals:",
            _format_goals(state.npc_profile.overt_goals),
            "remaining subtle goals:",
            _format_goals(state.npc_profile.subtle_goals),
        ]
    )
    app.logger.info("\n%s", log_message)


@app.get("/health")
def health() -> tuple[dict[str, str], int]:
    return {"status": "ok"}, 200


@app.post("/conversation/initialize")
def conversation_initialize():
    data = request.get_json(silent=True) or {}
    location = str(data.get("location") or DEFAULT_LOCATION)
    narrator_text = str(data.get("narrator_text") or DEFAULT_SCENE_INTRO)

    try:
        state = initialize_conversation(
            npc_profile=NPCProfile.love_patel(),
            location=location,
            narrator_text=narrator_text,
        )
        state = start_conversation(state)
        _log_conversation_state(action="conversation_initialize", state=state)
    except Exception as exc:  # pragma: no cover - defensive API boundary
        app.logger.exception("conversation_initialize failed")
        return jsonify({"error": str(exc)}), 500

    return jsonify(state.to_dict())


@app.post("/conversation/turn")
def conversation_turn():
    data = request.get_json(silent=True) or {}
    raw_state = data.get("state")
    user_input = data.get("user_input")

    if not isinstance(raw_state, dict):
        return jsonify({"error": "Missing or invalid 'state' object"}), 400
    if not isinstance(user_input, str) or not user_input.strip():
        return jsonify({"error": "Missing or invalid 'user_input' string"}), 400

    try:
        state = ConversationState.from_dict(raw_state)
        previous_hidden_metadata = dict(state.hidden_metadata)
        updated_state = run_turn(state, user_input)
        _log_conversation_state(
            action="conversation_turn",
            state=updated_state,
            previous_hidden_metadata=previous_hidden_metadata,
        )
    except Exception as exc:  # pragma: no cover - defensive API boundary
        app.logger.exception("conversation_turn failed")
        return jsonify({"error": str(exc)}), 500

    return jsonify(updated_state.to_dict())


if __name__ == "__main__":
    import os

    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    port = int(os.environ.get("PORT", "5000"))
    app.run(debug=debug, port=port)
