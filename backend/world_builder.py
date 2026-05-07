from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import logging
from typing import Any

from .location.destination_selector import SelectedDestination
from .location.models import LocationContext
from .npc_agent.conversation_state import ConversationState
from .npc_agent.runtime_profiles import build_destination_npc_profile, build_lodging_npc_profile
from .research.models import ResearchReport
from .world_state import RuntimeSceneDefinition, WorldState
from .world_store import build_canonical_lodging_fingerprint, generate_world_id

logger = logging.getLogger(__name__)


@dataclass
class BuiltWorld:
    world_state: WorldState
    conversation_state: ConversationState


class WorldBuilder:
    def build_world(
        self,
        *,
        location_context: LocationContext,
        research_report: ResearchReport,
        destinations: list[SelectedDestination],
        world_id: str | None = None,
    ) -> WorldState:
        resolved_world_id = world_id or generate_world_id()
        lodging_scene = self._build_lodging_scene(
            location_context=location_context,
            research_report=research_report,
            destinations=destinations,
            world_id=resolved_world_id,
        )
        travel_scenes = [self._build_travel_scene(destination, location_context, research_report) for destination in destinations]
        return WorldState(
            world_id=resolved_world_id,
            created_at=datetime.now(timezone.utc).isoformat(),
            fingerprint=build_canonical_lodging_fingerprint(location_context),
            location_context=location_context,
            research_report=research_report,
            lodging_scene=lodging_scene,
            travel_scenes=travel_scenes,
            generated_scene_cache={},
            generated_npc_cache={},
            metadata={"dynamic": True},
        )

    def build_initial_conversation(self, world_state: WorldState) -> ConversationState:
        return build_conversation_state_from_scene(
            world_state.lodging_scene,
            world_id=world_state.world_id,
            travel_scenes=world_state.travel_scenes,
            world_state=world_state,
        )

    def ensure_destination_generated(self, world_state: WorldState, location_id: str) -> RuntimeSceneDefinition:
        cached_scene = world_state.generated_scene_cache.get(location_id)
        if cached_scene is not None and cached_scene.npc_profile is not None:
            logger.info("lazy destination cache hit | world_id=%s | location_id=%s", world_state.world_id, location_id)
            return cached_scene

        base_scene = _find_scene(world_state, location_id)
        if base_scene is None:
            raise ValueError(f"Unknown destination location_id: {location_id}")

        if base_scene.npc_profile is None:
            logger.info("lazy destination generate | world_id=%s | location_id=%s | label=%s", world_state.world_id, location_id, base_scene.label)
            base_scene.npc_profile = build_destination_npc_profile(
                scene=base_scene,
                location_context=world_state.location_context,
                research_report=world_state.research_report,
                world_id=world_state.world_id,
            )

        if not base_scene.narrator_text:
            base_scene.narrator_text = self._build_destination_narrator_text(base_scene, world_state)

        world_state.generated_scene_cache[location_id] = base_scene
        world_state.generated_npc_cache[location_id] = base_scene.npc_profile
        return base_scene

    def _build_lodging_scene(
        self,
        *,
        location_context: LocationContext,
        research_report: ResearchReport,
        destinations: list[SelectedDestination],
        world_id: str,
    ) -> RuntimeSceneDefinition:
        local_anchor = location_context.neighborhood or location_context.city or location_context.country
        scene_label = location_context.canonical_name or "Your Lodging"
        description = (
            f"Arrive at {scene_label} and get your bearings before heading out into {local_anchor or 'the neighborhood'}."
        )
        location = self._build_lodging_location_string(location_context)
        narrator_text = self._build_lodging_narrator_text(location_context, research_report)
        travel_labels = [destination.label for destination in destinations]
        npc_profile = build_lodging_npc_profile(
            location_context=location_context,
            research_report=research_report,
            travel_scene_labels=travel_labels,
            world_id=world_id,
        )
        return RuntimeSceneDefinition(
            location_id="lodging",
            category="lodging",
            label=scene_label,
            description=description,
            location=location,
            narrator_text=narrator_text,
            place_metadata={
                "lodging_type": location_context.lodging_type,
                "formatted_address": location_context.formatted_address,
                "city": location_context.city,
                "neighborhood": location_context.neighborhood,
            },
            scene_seed={
                "arrival_mood": "freshly arrived traveler",
                "area_summary": research_report.area_summary,
            },
            npc_seed={
                "role": npc_profile.role,
                "lodging_type": location_context.lodging_type,
            },
            npc_profile=npc_profile,
        )

    def _build_travel_scene(
        self,
        destination: SelectedDestination,
        location_context: LocationContext,
        research_report: ResearchReport,
    ) -> RuntimeSceneDefinition:
        location = _build_destination_location_string(destination)
        narrator_text = _build_destination_stub_narration(destination, location_context, research_report)
        return RuntimeSceneDefinition(
            location_id=destination.location_id,
            category=destination.category,
            label=destination.label,
            description=destination.description,
            location=location,
            narrator_text=narrator_text,
            place_metadata=dict(destination.place_metadata),
            scene_seed=dict(destination.scene_seed),
            npc_seed=dict(destination.npc_seed),
            npc_profile=None,
        )

    def _build_lodging_location_string(self, location_context: LocationContext) -> str:
        name = location_context.canonical_name or "the lodging"
        lodging_type = (location_context.lodging_type or "lodging").lower()
        if lodging_type == "apartment":
            return f"the entrance and common space at {name}"
        if lodging_type == "guesthouse":
            return f"the front room of {name}"
        return f"the lobby of {name}"

    def _build_lodging_narrator_text(self, location_context: LocationContext, research_report: ResearchReport) -> str:
        name = location_context.canonical_name or "your lodging"
        area = location_context.neighborhood or location_context.city or "the surrounding neighborhood"
        area_summary = research_report.area_summary or f"The area around {area} feels immediately walkable and lived in."
        return (
            f"After the blur of transit, you arrive at {name} with your bag still in hand. "
            f"The first indoor quiet of the trip settles around you, and the place opens onto {area}, where {area_summary[0].lower() + area_summary[1:] if len(area_summary) > 1 else area_summary.lower()}."
        )

    def _build_destination_narrator_text(self, scene: RuntimeSceneDefinition, world_state: WorldState) -> str:
        return _build_destination_stub_narration(scene_to_destination(scene), world_state.location_context, world_state.research_report)


def build_conversation_state_from_scene(
    scene: RuntimeSceneDefinition,
    *,
    world_id: str | None,
    travel_scenes: list[RuntimeSceneDefinition],
    world_state: WorldState | None = None,
) -> ConversationState:
    if scene.npc_profile is None:
        raise ValueError(f"Scene {scene.location_id} is missing npc_profile")

    return ConversationState(
        location=scene.location,
        npc_profile=scene.npc_profile.__class__.from_dict(scene.npc_profile.to_dict()),
        scene_label=scene.label,
        scene_description=scene.description,
        location_id=scene.location_id,
        world_id=world_id,
        system_context=build_system_context(scene, travel_scenes=travel_scenes, world_state=world_state),
        available_travel_options=[build_travel_option_payload(item) for item in travel_scenes],
        conversation_history=[],
    )


def build_system_context(
    scene: RuntimeSceneDefinition,
    *,
    travel_scenes: list[RuntimeSceneDefinition],
    world_state: WorldState | None = None,
) -> dict[str, Any]:
    system_context = {
        "narrator_text": scene.narrator_text,
        "scene_label": scene.label,
        "scene_category": scene.category,
        "scene_description": scene.description,
        "scene_seed": dict(scene.scene_seed),
        "npc_seed": dict(scene.npc_seed),
        "place_metadata": dict(scene.place_metadata),
        "selected_destinations": [
            {
                "location_id": item.location_id,
                "label": item.label,
                "category": item.category,
                "description": item.description,
            }
            for item in travel_scenes
        ],
    }
    if world_state is not None:
        system_context["location_context"] = world_state.location_context.to_dict()
        system_context["research_report"] = world_state.research_report.to_dict()
        system_context["world_id"] = world_state.world_id
    return system_context


def build_travel_option_payload(scene: RuntimeSceneDefinition) -> dict[str, Any]:
    return {
        "location_id": scene.location_id,
        "category": scene.category,
        "label": scene.label,
        "description": scene.description,
        "location": scene.location,
        "narrator_text": scene.narrator_text,
    }


def _find_scene(world_state: WorldState, location_id: str) -> RuntimeSceneDefinition | None:
    if world_state.lodging_scene.location_id == location_id:
        return world_state.lodging_scene
    for scene in world_state.travel_scenes:
        if scene.location_id == location_id:
            return scene
    return None


def _build_destination_location_string(destination: SelectedDestination) -> str:
    category = destination.category
    label = destination.label
    if category == "cafe":
        return f"the counter and seating area at {label}"
    if category == "bookstore":
        return f"the shelves and reading corners of {label}"
    return f"the open-air paths and gathering spots around {label}"


def _build_destination_stub_narration(
    destination: SelectedDestination | RuntimeSceneDefinition,
    location_context: LocationContext,
    research_report: ResearchReport,
) -> str:
    area = location_context.neighborhood or location_context.city or "the area nearby"
    note = (research_report.destination_recommendation_notes[:1] or [f"It feels like a natural next stop from {location_context.canonical_name or 'the lodging'}. "])[0]
    return (
        f"A short move from your lodging brings you to {destination.label}, where the atmosphere shifts just enough to make the neighborhood feel more tangible. "
        f"Around {area}, this kind of stop makes sense: {note.rstrip('.')} ."
    ).replace(" .", ".")


def scene_to_destination(scene: RuntimeSceneDefinition) -> SelectedDestination:
    return SelectedDestination(
        location_id=scene.location_id,
        category=scene.category,
        label=scene.label,
        description=scene.description,
        place_metadata=dict(scene.place_metadata),
        scene_seed=dict(scene.scene_seed),
        npc_seed=dict(scene.npc_seed),
    )
