from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

from .conversation_state import ConversationState, DialogueTurn
from .npc_profile import NPCProfile
from .prompts.defaults import TRAVEL_SELECTION_SUFFIX, is_travel_selection_location
from .scenes import TRAVEL_DESTINATIONS, SceneDefinition, get_initial_scene

STATIC_ROOT = Path(__file__).resolve().parents[1] / "static"
GENERATED_ROOT = STATIC_ROOT / "generated"
SCENE_DIR = GENERATED_ROOT / "scenes"
NPC_DIR = GENERATED_ROOT / "npcs"

SCENE_ART_STYLE = (
    "cinematic semi-realistic digital illustration for a narrative travel adventure game, "
    "rich environmental storytelling, polished concept-art quality, grounded lighting, no text, no UI"
)
NPC_ART_STYLE = (
    "stylized semi-realistic digital character portrait for a narrative travel adventure game, "
    "clean head-and-shoulders framing, expressive natural lighting, polished concept-art quality, no text, no UI"
)


@dataclass(frozen=True)
class ImageAssetSpec:
    kind: str
    key: str
    label: str
    prompt: str
    relative_path: str
    metadata_relative_path: str
    source: dict[str, str]

    @property
    def output_path(self) -> Path:
        return STATIC_ROOT / self.relative_path

    @property
    def metadata_path(self) -> Path:
        return STATIC_ROOT / self.metadata_relative_path

    @property
    def url_path(self) -> str:
        return f"/static/{self.relative_path.replace('\\', '/')}"


def ensure_generated_directories() -> None:
    SCENE_DIR.mkdir(parents=True, exist_ok=True)
    NPC_DIR.mkdir(parents=True, exist_ok=True)


def build_scene_asset_spec(*, location: str, narrator_text: str, label: str | None = None) -> ImageAssetSpec:
    normalized_location = (location or "unknown scene").strip()
    normalized_narration = (narrator_text or "").strip()
    slug = _slugify(normalized_location) or "scene"
    digest = _hash_parts(normalized_location, normalized_narration)
    key = f"{slug}-{digest}"

    return ImageAssetSpec(
        kind="scene_background",
        key=key,
        label=label or normalized_location.title(),
        prompt=build_scene_image_prompt(location=normalized_location, narrator_text=normalized_narration),
        relative_path=f"generated/scenes/{key}.png",
        metadata_relative_path=f"generated/scenes/{key}.json",
        source={
            "location": normalized_location,
            "narrator_text": normalized_narration,
        },
    )


def build_npc_asset_spec(npc_profile: NPCProfile) -> ImageAssetSpec:
    name = (npc_profile.name or "npc").strip()
    role = (npc_profile.role or "").strip()
    slug = _slugify(name) or "npc"
    digest = _hash_parts(
        name,
        role,
        npc_profile.physical_description,
        npc_profile.mental_description,
        npc_profile.emotional_description,
        npc_profile.local_flavor,
    )
    key = f"{slug}-{digest}"

    return ImageAssetSpec(
        kind="npc_headshot",
        key=key,
        label=name,
        prompt=build_npc_headshot_prompt(npc_profile),
        relative_path=f"generated/npcs/{key}.png",
        metadata_relative_path=f"generated/npcs/{key}.json",
        source={
            "name": name,
            "role": role,
            "physical_description": npc_profile.physical_description,
            "mental_description": npc_profile.mental_description,
            "emotional_description": npc_profile.emotional_description,
            "local_flavor": npc_profile.local_flavor,
        },
    )


def build_scene_image_prompt(*, location: str, narrator_text: str) -> str:
    return (
        f"Create a scene background image for a browser-based narrative RPG. Style: {SCENE_ART_STYLE}. "
        "Focus on the environment and mood rather than a character portrait. "
        "If people appear, they should be small and incidental in the composition. "
        f"Location: {location}. "
        f"Narration: {narrator_text}."
    )


def build_npc_headshot_prompt(npc_profile: NPCProfile) -> str:
    return (
        f"Create an NPC portrait for a browser-based narrative RPG. Style: {NPC_ART_STYLE}. "
        "Single character only, framed from the shoulders up, with a neutral background or softly implied setting. "
        f"Name: {npc_profile.name}. "
        f"Role: {npc_profile.role}. "
        f"Physical description: {npc_profile.physical_description}. "
        f"Mental vibe: {npc_profile.mental_description}. "
        f"Emotional vibe: {npc_profile.emotional_description}. "
        f"Setting flavor: {npc_profile.local_flavor}."
    )


def build_static_asset_specs(kind: str = "all") -> list[ImageAssetSpec]:
    specs: dict[str, ImageAssetSpec] = {}
    scenes = [get_initial_scene(), *TRAVEL_DESTINATIONS]

    include_scenes = kind in {"all", "scenes"}
    include_npcs = kind in {"all", "npcs"}

    for scene in scenes:
        if include_scenes:
            scene_spec = build_scene_asset_spec(
                location=scene.location,
                narrator_text=scene.narrator_text,
                label=scene.label,
            )
            specs[f"{scene_spec.kind}:{scene_spec.key}"] = scene_spec

        if include_npcs:
            npc_spec = build_npc_asset_spec(scene.npc_factory())
            specs[f"{npc_spec.kind}:{npc_spec.key}"] = npc_spec

    return sorted(specs.values(), key=lambda spec: (spec.kind, spec.label.lower(), spec.key))


def build_static_asset_manifest() -> dict[str, Any]:
    assets = [_describe_asset(spec) for spec in build_static_asset_specs()]
    return {
        "generated_root": str(GENERATED_ROOT),
        "counts": {
            "total": len(assets),
            "available": sum(1 for asset in assets if asset["exists"]),
            "missing": sum(1 for asset in assets if not asset["exists"]),
        },
        "assets": assets,
    }


def build_rendering_context(state: ConversationState) -> dict[str, Any]:
    base_location = _strip_travel_selection_suffix(state.location)
    narrator_text = _find_first_turn_dialogue(state.conversation_history, speaker="Narrator")
    matched_scene = _find_scene_by_location(base_location)

    scene_label = matched_scene.label if matched_scene else _humanize_location(base_location)
    scene_spec = build_scene_asset_spec(
        location=base_location,
        narrator_text=narrator_text or (matched_scene.narrator_text if matched_scene else ""),
        label=scene_label,
    )
    npc_spec = build_npc_asset_spec(state.npc_profile)

    return {
        "scene": {
            "label": scene_label,
            "location": base_location,
            "background": _describe_runtime_asset(scene_spec),
        },
        "npc": {
            "name": state.npc_profile.name,
            "role": state.npc_profile.role,
            "headshot": _describe_runtime_asset(npc_spec),
        },
        "travel_selection": is_travel_selection_location(state.location),
        "travel_options": [_build_travel_option_rendering(scene) for scene in TRAVEL_DESTINATIONS],
    }


def _build_travel_option_rendering(scene: SceneDefinition) -> dict[str, Any]:
    scene_spec = build_scene_asset_spec(
        location=scene.location,
        narrator_text=scene.narrator_text,
        label=scene.label,
    )
    npc_profile = scene.npc_factory()
    npc_spec = build_npc_asset_spec(npc_profile)

    return {
        "location_id": scene.location_id,
        "label": scene.label,
        "description": scene.description,
        "command": f"/command {_travel_command_number(scene.location_id)}",
        "background": _describe_runtime_asset(scene_spec),
        "npc": {
            "name": npc_profile.name,
            "role": npc_profile.role,
            "headshot": _describe_runtime_asset(npc_spec),
        },
    }


def _travel_command_number(location_id: str) -> int:
    for index, scene in enumerate(TRAVEL_DESTINATIONS, start=1):
        if scene.location_id == location_id:
            return index
    return 1


def _describe_runtime_asset(spec: ImageAssetSpec) -> dict[str, Any]:
    exists = spec.output_path.is_file()
    return {
        "key": spec.key,
        "exists": exists,
        "url": spec.url_path if exists else None,
        "relative_path": spec.relative_path,
    }


def _describe_asset(spec: ImageAssetSpec) -> dict[str, Any]:
    exists = spec.output_path.is_file()
    return {
        "kind": spec.kind,
        "key": spec.key,
        "label": spec.label,
        "exists": exists,
        "url": spec.url_path if exists else None,
        "relative_path": spec.relative_path,
        "metadata_relative_path": spec.metadata_relative_path,
        "source": spec.source,
    }


def _find_scene_by_location(location: str) -> SceneDefinition | None:
    normalized_location = location.strip()
    for scene in [get_initial_scene(), *TRAVEL_DESTINATIONS]:
        if scene.location == normalized_location:
            return scene
    return None


def _find_first_turn_dialogue(turns: list[DialogueTurn], *, speaker: str) -> str | None:
    for turn in turns:
        if turn.speaker == speaker and turn.dialogue.strip():
            return turn.dialogue.strip()
    return None


def _strip_travel_selection_suffix(location: str) -> str:
    if location.endswith(TRAVEL_SELECTION_SUFFIX):
        return location[: -len(TRAVEL_SELECTION_SUFFIX)].rstrip()
    return location


def _hash_parts(*parts: str) -> str:
    payload = "\n".join((part or "").strip() for part in parts)
    return sha256(payload.encode("utf-8")).hexdigest()[:12]


def _slugify(value: str) -> str:
    words = "".join(ch.lower() if ch.isalnum() else " " for ch in value).split()
    return "-".join(words[:8])


def _humanize_location(location: str) -> str:
    if not location:
        return "Unknown Scene"
    words = location.replace("_", " ").replace("-", " ").split()
    if not words:
        return "Unknown Scene"
    return " ".join(word.capitalize() for word in words)
