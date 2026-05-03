from __future__ import annotations

from flask import Flask, jsonify, request

from backend.npc_agent.agent import initialize_conversation, run_turn, start_conversation
from backend.npc_agent.conversation_state import ConversationState
from backend.npc_agent.npc_profile import NPCProfile

app = Flask(__name__)

DEFAULT_LOCATION = "the lobby of a grand city hotel"
DEFAULT_SCENE_INTRO = (
    "After a sleepless red-eye, you step into the hotel lobby with your carry-on still in hand. "
    "The room is all warm light, polished stone, and low conversation, and the front desk ahead of you "
    "feels like the first real pause since you left the airport. Behind it stands Love Patel, alert and "
    "welcoming, already looking up as you arrive."
)


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
    except Exception as exc:  # pragma: no cover - defensive API boundary
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
        updated_state = run_turn(state, user_input)
    except Exception as exc:  # pragma: no cover - defensive API boundary
        return jsonify({"error": str(exc)}), 500

    return jsonify(updated_state.to_dict())


if __name__ == "__main__":
    import os

    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    port = int(os.environ.get("PORT", "5000"))
    app.run(debug=debug, port=port)
