from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

try:
    from backend.location.models import LocationContext
    from backend.npc_agent.npc_profile import NPCProfile
    from backend.research.models import ResearchReport
except ModuleNotFoundError:
    from location.models import LocationContext
    from npc_agent.npc_profile import NPCProfile
    from research.models import ResearchReport


@dataclass
class RuntimeSceneDefinition:
    """Dynamic equivalent of the static scene definition."""

    location_id: str
    category: str
    label: str
    description: str
    location: str
    narrator_text: str
    place_metadata: dict[str, Any] = field(default_factory=dict)
    scene_seed: dict[str, Any] = field(default_factory=dict)
    npc_seed: dict[str, Any] = field(default_factory=dict)
    npc_profile: NPCProfile | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "location_id": self.location_id,
            "category": self.category,
            "label": self.label,
            "description": self.description,
            "location": self.location,
            "narrator_text": self.narrator_text,
            "place_metadata": _normalize_dict(self.place_metadata),
            "scene_seed": _normalize_dict(self.scene_seed),
            "npc_seed": _normalize_dict(self.npc_seed),
            "npc_profile": self.npc_profile.to_dict() if self.npc_profile else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RuntimeSceneDefinition":
        npc_profile_data = data.get("npc_profile")
        return cls(
            location_id=str(data.get("location_id", "")),
            category=str(data.get("category", "")),
            label=str(data.get("label", "")),
            description=str(data.get("description", "")),
            location=str(data.get("location", "")),
            narrator_text=str(data.get("narrator_text", "")),
            place_metadata=_normalize_dict(data.get("place_metadata", {})),
            scene_seed=_normalize_dict(data.get("scene_seed", {})),
            npc_seed=_normalize_dict(data.get("npc_seed", {})),
            npc_profile=NPCProfile.from_dict(npc_profile_data) if isinstance(npc_profile_data, dict) else None,
        )


@dataclass
class WorldState:
    """Persistent container for a generated lodging-driven world."""

    world_id: str
    created_at: str
    fingerprint: str
    location_context: LocationContext
    research_report: ResearchReport
    lodging_scene: RuntimeSceneDefinition
    travel_scenes: list[RuntimeSceneDefinition] = field(default_factory=list)
    generated_scene_cache: dict[str, RuntimeSceneDefinition] = field(default_factory=dict)
    generated_npc_cache: dict[str, NPCProfile] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "world_id": self.world_id,
            "created_at": self.created_at,
            "fingerprint": self.fingerprint,
            "location_context": self.location_context.to_dict(),
            "research_report": self.research_report.to_dict(),
            "lodging_scene": self.lodging_scene.to_dict(),
            "travel_scenes": [scene.to_dict() for scene in self.travel_scenes],
            "generated_scene_cache": {
                str(location_id): scene.to_dict()
                for location_id, scene in self.generated_scene_cache.items()
            },
            "generated_npc_cache": {
                str(location_id): profile.to_dict()
                for location_id, profile in self.generated_npc_cache.items()
            },
            "metadata": _normalize_dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorldState":
        raw_generated_scene_cache = data.get("generated_scene_cache", {})
        raw_generated_npc_cache = data.get("generated_npc_cache", {})

        return cls(
            world_id=str(data.get("world_id", "")),
            created_at=str(data.get("created_at", "")),
            fingerprint=str(data.get("fingerprint", "")),
            location_context=LocationContext.from_dict(_normalize_dict(data.get("location_context", {}))),
            research_report=ResearchReport.from_dict(_normalize_dict(data.get("research_report", {}))),
            lodging_scene=RuntimeSceneDefinition.from_dict(_normalize_dict(data.get("lodging_scene", {}))),
            travel_scenes=[
                RuntimeSceneDefinition.from_dict(item)
                for item in data.get("travel_scenes", [])
                if isinstance(item, dict)
            ],
            generated_scene_cache={
                str(location_id): RuntimeSceneDefinition.from_dict(scene)
                for location_id, scene in raw_generated_scene_cache.items()
                if isinstance(scene, dict)
            }
            if isinstance(raw_generated_scene_cache, dict)
            else {},
            generated_npc_cache={
                str(location_id): NPCProfile.from_dict(profile)
                for location_id, profile in raw_generated_npc_cache.items()
                if isinstance(profile, dict)
            }
            if isinstance(raw_generated_npc_cache, dict)
            else {},
            metadata=_normalize_dict(data.get("metadata", {})),
        )


def _normalize_dict(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {str(key): item for key, item in value.items()}
