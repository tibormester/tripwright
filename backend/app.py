from __future__ import annotations

import logging
from pathlib import Path
import time

from flask import Flask, jsonify, request

try:
    from backend.config import AppConfig
    from backend.generate_assets import build_runtime_specs_for_scene, generate_asset_specs
    from backend.location import DestinationSelector, LodgingResolutionService
    from backend.location.providers import OverpassProvider
    from backend.npc_agent.agent import initialize_conversation, run_turn, start_conversation
    from backend.npc_agent.assets import build_rendering_context, build_static_asset_manifest
    from backend.npc_agent.conversation_state import ConversationState, DialogueTurn
    from backend.npc_agent.scenes import build_travel_options, get_initial_scene
    from backend.research import ResearchService
    from backend.world_builder import WorldBuilder
    from backend.world_store import build_canonical_lodging_fingerprint, create_world_store
except ModuleNotFoundError:
    from config import AppConfig
    from generate_assets import build_runtime_specs_for_scene, generate_asset_specs
    from location import DestinationSelector, LodgingResolutionService
    from location.providers import OverpassProvider
    from npc_agent.agent import initialize_conversation, run_turn, start_conversation
    from npc_agent.assets import build_rendering_context, build_static_asset_manifest
    from npc_agent.conversation_state import ConversationState, DialogueTurn
    from npc_agent.scenes import build_travel_options, get_initial_scene
    from research import ResearchService
    from world_builder import WorldBuilder
    from world_store import build_canonical_lodging_fingerprint, create_world_store

PUBLIC_DIR = Path(__file__).resolve().parents[1] / "public"
app = Flask(__name__, static_folder=str(PUBLIC_DIR), static_url_path="")

if not app.logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
app.logger.setLevel(logging.INFO)

config = AppConfig.from_env()
world_store = create_world_store(config)
lodging_resolution_service = LodgingResolutionService(config)
destination_selector = DestinationSelector(
    OverpassProvider(
        timeout_seconds=config.provider_timeout_seconds,
        max_retries=config.provider_max_retries,
    )
)
research_service = ResearchService(config)
world_builder = WorldBuilder()


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
            f"world_id: {_format_inline(state.world_id)}",
            f"scene_label: {_format_inline(state.scene_label)}",
            f"user: {_format_inline(user_turn.dialogue if user_turn else None)}",
            f"npc dialogue: {_format_inline(npc_turn.dialogue if npc_turn else None)}",
            f"npc thinking: {_format_inline(npc_turn.thinking if npc_turn else None)}",
            f"location: {_format_inline(state.location)}",
            "flags:",
            _format_flags(new_flags),
            "remaining overt goals:",
            _format_goals(state.npc_profile.overt_goals),
            "remaining subtle goals:",
            _format_goals(state.npc_profile.subtle_goals),
        ]
    )
    app.logger.info("\n%s", log_message)


def _serialize_state_payload(state: ConversationState) -> dict:
    payload = state.to_dict()
    payload["rendering"] = build_rendering_context(state)
    return payload


def _serialize_state_response(state: ConversationState):
    return jsonify(_serialize_state_payload(state))


@app.get("/")
def index():
    return app.send_static_file("index.html")


@app.get("/health")
def health() -> tuple[dict[str, str], int]:
    return {"status": "ok"}, 200


@app.get("/assets/manifest")
def assets_manifest():
    return jsonify(build_static_asset_manifest())


def _best_effort_generate_runtime_assets(state: ConversationState) -> None:
    if not config.enable_image_generation:
        return
    try:
        narrator_text = ""
        if isinstance(state.system_context, dict):
            narrator_text = str(state.system_context.get("narrator_text", ""))
        specs = build_runtime_specs_for_scene(
            scene_label=state.scene_label,
            location=state.location,
            narrator_text=narrator_text,
            npc_profile=state.npc_profile,
            travel_options=state.available_travel_options,
        )
        generate_asset_specs(
            specs=specs,
            force=False,
            dry_run=False,
            model="gpt-image-1",
            size="1024x1024",
            best_effort=True,
        )
    except Exception as exc:  # pragma: no cover - best effort only
        app.logger.warning("runtime asset generation skipped | scene=%s | error=%s", state.scene_label, exc)


def _build_static_fallback_response(*, reason: str, requested_lodging_input: str | None = None):
    initial_scene = get_initial_scene()
    fallback_note = (
        f"Dynamic world setup was unavailable, so TripWright started fallback scene data instead. Reason: {reason}."
    )
    state = initialize_conversation(
        npc_profile=initial_scene.npc_factory(),
        location=initial_scene.location,
        narrator_text=initial_scene.narrator_text,
        scene_label=f"{initial_scene.label} (Fallback)",
        scene_description=fallback_note,
        location_id=initial_scene.location_id,
        system_context={"fallback_mode": True, "fallback_reason": reason, "narrator_text": initial_scene.narrator_text},
        available_travel_options=build_travel_options(),
    )
    state = start_conversation(state)
    _best_effort_generate_runtime_assets(state)
    _log_conversation_state(action="static_fallback_initialize", state=state)
    return jsonify(
        {
            "world_id": None,
            "world": None,
            "conversation": _serialize_state_payload(state),
            "cache_hit": False,
            "fallback_mode": True,
            "fallback_reason": reason,
        }
    )


@app.post("/world/initialize")
def world_initialize():
    data = request.get_json(silent=True) or {}
    lodging_input = str(data.get("lodging_input", "")).strip()
    if not lodging_input:
        return jsonify({"error": "Missing or invalid 'lodging_input' string"}), 400

    try:
        started_at = time.perf_counter()
        app.logger.info("world initialize start | input=%s", lodging_input)
        resolution_result = lodging_resolution_service.resolve(lodging_input)
        location_context = resolution_result.location_context
        app.logger.info(
            "world initialize resolved | provider=%s | confidence=%.2f | canonical_name=%s | address=%s | coords=%s,%s",
            location_context.provider,
            location_context.resolution_confidence,
            location_context.canonical_name,
            location_context.formatted_address,
            location_context.latitude,
            location_context.longitude,
        )
        fingerprint = build_canonical_lodging_fingerprint(location_context)
        existing_world_id = world_store.find_world_id_by_fingerprint(fingerprint)

        if existing_world_id:
            world_state = world_store.get_world(existing_world_id)
            if world_state is not None:
                app.logger.info("world initialize cache hit | world_id=%s | fingerprint=%s", existing_world_id, fingerprint)
                conversation_state = world_builder.build_initial_conversation(world_state)
                conversation_state = start_conversation(conversation_state)
                _best_effort_generate_runtime_assets(conversation_state)
                _log_conversation_state(action="world_initialize_cache_hit", state=conversation_state)
                return jsonify(
                    {
                        "world_id": world_state.world_id,
                        "world": world_state.to_dict(),
                        "conversation": _serialize_state_payload(conversation_state),
                        "cache_hit": True,
                    }
                )

        research_report = research_service.research_area(location_context)
        destinations = destination_selector.select_destinations(
            latitude=location_context.latitude,
            longitude=location_context.longitude,
            location_context=location_context,
        )
        world_state = world_builder.build_world(
            location_context=location_context,
            research_report=research_report,
            destinations=destinations,
        )
        app.logger.info(
            "world initialize destinations | world_id=%s | destinations=%s",
            world_state.world_id,
            [f"{item.category}:{item.label}" for item in destinations],
        )
        world_store.save_world(world_state)
        world_store.save_fingerprint_mapping(world_state.fingerprint, world_state.world_id)

        conversation_state = world_builder.build_initial_conversation(world_state)
        conversation_state = start_conversation(conversation_state)
        _best_effort_generate_runtime_assets(conversation_state)
        _log_conversation_state(action="world_initialize", state=conversation_state)
        app.logger.info(
            "world initialize complete | world_id=%s | duration_ms=%s",
            world_state.world_id,
            int((time.perf_counter() - started_at) * 1000),
        )
        return jsonify(
            {
                "world_id": world_state.world_id,
                "world": world_state.to_dict(),
                "conversation": _serialize_state_payload(conversation_state),
                "cache_hit": False,
            }
        )
    except ValueError as exc:
        app.logger.warning("world_initialize dynamic failed, using fallback scene data: %s", exc)
        return _build_static_fallback_response(reason=str(exc), requested_lodging_input=lodging_input)
    except Exception as exc:  # pragma: no cover - defensive API boundary
        app.logger.exception("world_initialize failed; using fallback scene data")
        return _build_static_fallback_response(reason=str(exc), requested_lodging_input=lodging_input)


@app.post("/conversation/initialize")
def conversation_initialize():
    data = request.get_json(silent=True) or {}
    initial_scene = get_initial_scene()
    location = str(data.get("location") or initial_scene.location)
    narrator_text = str(data.get("narrator_text") or initial_scene.narrator_text)

    try:
        state = initialize_conversation(
            npc_profile=initial_scene.npc_factory(),
            location=location,
            narrator_text=narrator_text,
            scene_label=initial_scene.label,
            scene_description=initial_scene.description,
            location_id=initial_scene.location_id,
            available_travel_options=build_travel_options(),
        )
        state = start_conversation(state)
        _best_effort_generate_runtime_assets(state)
        _log_conversation_state(action="conversation_initialize", state=state)
    except Exception as exc:  # pragma: no cover - defensive API boundary
        app.logger.exception("conversation_initialize failed")
        return jsonify({"error": str(exc)}), 500

    return _serialize_state_response(state)


@app.post("/conversation/turn")
def conversation_turn():
    data = request.get_json(silent=True) or {}
    raw_state = data.get("state")
    user_input = data.get("user_input")
    world_id = data.get("world_id")

    if not isinstance(raw_state, dict):
        return jsonify({"error": "Missing or invalid 'state' object"}), 400
    if not isinstance(user_input, str) or not user_input.strip():
        return jsonify({"error": "Missing or invalid 'user_input' string"}), 400

    try:
        state = ConversationState.from_dict(raw_state)
        previous_hidden_metadata = dict(state.hidden_metadata)

        effective_world_id = str(world_id or state.world_id or "").strip() or None
        world_state = world_store.get_world(effective_world_id) if effective_world_id else None
        if effective_world_id and world_state is None:
            return jsonify({"error": f"Unknown world_id: {effective_world_id}"}), 404
        app.logger.info(
            "conversation turn start | world_id=%s | location_id=%s | scene_label=%s | user_input=%s",
            effective_world_id,
            state.location_id,
            state.scene_label,
            user_input,
        )
        updated_state = run_turn(
            state,
            user_input,
            world_state=world_state,
            world_builder=world_builder,
        )
        if world_state is not None:
            world_store.save_world(world_state)
        _best_effort_generate_runtime_assets(updated_state)

        _log_conversation_state(
            action="conversation_turn",
            state=updated_state,
            previous_hidden_metadata=previous_hidden_metadata,
        )
    except Exception as exc:  # pragma: no cover - defensive API boundary
        app.logger.exception("conversation_turn failed")
        return jsonify({"error": str(exc)}), 500

    return _serialize_state_response(updated_state)


if __name__ == "__main__":
    import os

    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    port = int(os.environ.get("PORT", "5000"))
    app.run(debug=debug, port=port)
