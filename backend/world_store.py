from __future__ import annotations

import json
from abc import ABC, abstractmethod
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

try:
    from backend.config import AppConfig
    from backend.location.models import LocationContext
    from backend.world_state import WorldState
except ModuleNotFoundError:
    from config import AppConfig
    from location.models import LocationContext
    from world_state import WorldState


class WorldStore(ABC):
    """Persistence abstraction for generated worlds."""

    @abstractmethod
    def get_world(self, world_id: str) -> WorldState | None:
        raise NotImplementedError

    @abstractmethod
    def save_world(self, world_state: WorldState) -> None:
        raise NotImplementedError

    @abstractmethod
    def find_world_id_by_fingerprint(self, fingerprint: str) -> str | None:
        raise NotImplementedError

    @abstractmethod
    def save_fingerprint_mapping(self, fingerprint: str, world_id: str) -> None:
        raise NotImplementedError


class MemoryWorldStore(WorldStore):
    def __init__(self) -> None:
        self._worlds: dict[str, WorldState] = {}
        self._fingerprint_index: dict[str, str] = {}

    def get_world(self, world_id: str) -> WorldState | None:
        return self._worlds.get(world_id)

    def save_world(self, world_state: WorldState) -> None:
        self._worlds[world_state.world_id] = world_state

    def find_world_id_by_fingerprint(self, fingerprint: str) -> str | None:
        return self._fingerprint_index.get(fingerprint)

    def save_fingerprint_mapping(self, fingerprint: str, world_id: str) -> None:
        self._fingerprint_index[fingerprint] = world_id


class FileWorldStore(WorldStore):
    def __init__(self, data_root: str | Path = "data") -> None:
        self.data_root = Path(data_root)
        self.index_path = self.data_root / "world_index.json"
        self.worlds_root = self.data_root / "worlds"
        self.data_root.mkdir(parents=True, exist_ok=True)
        self.worlds_root.mkdir(parents=True, exist_ok=True)
        if not self.index_path.exists():
            self._write_json(self.index_path, {})

    def get_world(self, world_id: str) -> WorldState | None:
        world_path = self._world_path(world_id)
        if not world_path.exists():
            return None
        return WorldState.from_dict(self._read_json(world_path))

    def save_world(self, world_state: WorldState) -> None:
        world_path = self._world_path(world_state.world_id)
        world_path.parent.mkdir(parents=True, exist_ok=True)
        self._write_json(world_path, world_state.to_dict())

    def find_world_id_by_fingerprint(self, fingerprint: str) -> str | None:
        index = self._load_index()
        world_id = index.get(fingerprint)
        if world_id is None:
            return None
        return str(world_id)

    def save_fingerprint_mapping(self, fingerprint: str, world_id: str) -> None:
        index = self._load_index()
        index[fingerprint] = world_id
        self._write_json(self.index_path, index)

    def _load_index(self) -> dict[str, str]:
        raw_index = self._read_json(self.index_path)
        if not isinstance(raw_index, dict):
            return {}
        return {str(key): str(value) for key, value in raw_index.items()}

    def _world_path(self, world_id: str) -> Path:
        return self.worlds_root / world_id / "world.json"

    def _read_json(self, path: Path) -> dict:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {}

    def _write_json(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_suffix(path.suffix + ".tmp")
        temp_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
        temp_path.replace(path)


def build_canonical_lodging_fingerprint(location_context: LocationContext) -> str:
    parts = [
        _normalize_text(location_context.canonical_name),
        _normalize_text(location_context.formatted_address),
        _normalize_text(location_context.city),
        _normalize_text(location_context.region),
        _normalize_text(location_context.country),
        _normalize_coordinate(location_context.latitude),
        _normalize_coordinate(location_context.longitude),
    ]
    payload = "|".join(parts)
    return f"lodging_{sha256(payload.encode('utf-8')).hexdigest()[:24]}"


def generate_world_id(prefix: str = "lodg") -> str:
    return f"{prefix}_{uuid4().hex[:16]}"


def create_world_store(config: AppConfig | None = None) -> WorldStore:
    resolved_config = config or AppConfig.from_env()
    if resolved_config.world_store_mode == "file":
        return FileWorldStore(resolved_config.world_data_dir)
    return MemoryWorldStore()


def _normalize_text(value: str | None) -> str:
    if not value:
        return ""
    return " ".join("".join(ch.lower() if ch.isalnum() else " " for ch in value).split())


def _normalize_coordinate(value: float | None) -> str:
    if value is None:
        return ""
    return f"{float(value):.4f}"
