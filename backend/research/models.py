from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ResearchReport:
    """Structured local-flavor research used by the runtime world builder."""

    area_summary: str = ""
    tone_keywords: list[str] = field(default_factory=list)
    local_sayings: list[str] = field(default_factory=list)
    demographic_archetypes: list[str] = field(default_factory=list)
    common_hobbies: list[str] = field(default_factory=list)
    social_norms: list[str] = field(default_factory=list)
    lodging_context: str = ""
    destination_recommendation_notes: list[str] = field(default_factory=list)
    sources: list[dict[str, str]] = field(default_factory=list)
    raw_snippets: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "area_summary": self.area_summary,
            "tone_keywords": list(self.tone_keywords),
            "local_sayings": list(self.local_sayings),
            "demographic_archetypes": list(self.demographic_archetypes),
            "common_hobbies": list(self.common_hobbies),
            "social_norms": list(self.social_norms),
            "lodging_context": self.lodging_context,
            "destination_recommendation_notes": list(self.destination_recommendation_notes),
            "sources": [_normalize_string_map(item) for item in self.sources],
            "raw_snippets": [_normalize_string_map(item) for item in self.raw_snippets],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ResearchReport":
        return cls(
            area_summary=str(data.get("area_summary", "")),
            tone_keywords=_normalize_string_list(data.get("tone_keywords", [])),
            local_sayings=_normalize_string_list(data.get("local_sayings", [])),
            demographic_archetypes=_normalize_string_list(data.get("demographic_archetypes", [])),
            common_hobbies=_normalize_string_list(data.get("common_hobbies", [])),
            social_norms=_normalize_string_list(data.get("social_norms", [])),
            lodging_context=str(data.get("lodging_context", "")),
            destination_recommendation_notes=_normalize_string_list(data.get("destination_recommendation_notes", [])),
            sources=_normalize_string_map_list(data.get("sources", [])),
            raw_snippets=_normalize_string_map_list(data.get("raw_snippets", [])),
        )


def _normalize_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _normalize_string_map(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {str(key): str(item) for key, item in value.items()}


def _normalize_string_map_list(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    return [_normalize_string_map(item) for item in value if isinstance(item, dict)]
