from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class LocationContext:
    """Canonical metadata for a resolved lodging or place input."""

    input_value: str
    input_kind: str
    source_url: str | None = None
    canonical_name: str = ""
    formatted_address: str = ""
    latitude: float | None = None
    longitude: float | None = None
    city: str = ""
    neighborhood: str = ""
    region: str = ""
    country: str = ""
    lodging_type: str = "unknown"
    provider: str = ""
    provider_place_id: str = ""
    resolution_confidence: float = 0.0
    raw_metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "input_value": self.input_value,
            "input_kind": self.input_kind,
            "source_url": self.source_url,
            "canonical_name": self.canonical_name,
            "formatted_address": self.formatted_address,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "city": self.city,
            "neighborhood": self.neighborhood,
            "region": self.region,
            "country": self.country,
            "lodging_type": self.lodging_type,
            "provider": self.provider,
            "provider_place_id": self.provider_place_id,
            "resolution_confidence": self.resolution_confidence,
            "raw_metadata": self.raw_metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LocationContext":
        return cls(
            input_value=str(data.get("input_value", "")),
            input_kind=str(data.get("input_kind", "")),
            source_url=_normalize_optional_str(data.get("source_url")),
            canonical_name=str(data.get("canonical_name", "")),
            formatted_address=str(data.get("formatted_address", "")),
            latitude=_normalize_optional_float(data.get("latitude")),
            longitude=_normalize_optional_float(data.get("longitude")),
            city=str(data.get("city", "")),
            neighborhood=str(data.get("neighborhood", "")),
            region=str(data.get("region", "")),
            country=str(data.get("country", "")),
            lodging_type=str(data.get("lodging_type", "unknown") or "unknown"),
            provider=str(data.get("provider", "")),
            provider_place_id=str(data.get("provider_place_id", "")),
            resolution_confidence=_normalize_optional_float(data.get("resolution_confidence")) or 0.0,
            raw_metadata=_normalize_dict(data.get("raw_metadata", {})),
        )


def _normalize_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_dict(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {str(key): item for key, item in value.items()}
