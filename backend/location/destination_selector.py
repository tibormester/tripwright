from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import logging
from typing import Any

from .models import LocationContext
from .providers import OverpassPlace, OverpassProvider

logger = logging.getLogger(__name__)

DEFAULT_SEARCH_RADIUS_METERS = 1800

CATEGORY_FILTERS: dict[str, list[tuple[str, str]]] = {
    "cafe": [("amenity", "cafe"), ("amenity", "coffee_shop"), ("shop", "bakery")],
    "bookstore": [("shop", "books"), ("amenity", "library")],
    "park": [
        ("leisure", "park"),
        ("leisure", "garden"),
        ("place", "square"),
        ("highway", "pedestrian"),
        ("natural", "water"),
    ],
}

CATEGORY_FALLBACKS: dict[str, list[str]] = {
    "cafe": ["cafe"],
    "bookstore": ["bookstore", "cafe"],
    "park": ["park"],
}


@dataclass
class SelectedDestination:
    location_id: str
    category: str
    label: str
    description: str
    place_metadata: dict[str, Any]
    scene_seed: dict[str, Any]
    npc_seed: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "location_id": self.location_id,
            "category": self.category,
            "label": self.label,
            "description": self.description,
            "place_metadata": self.place_metadata,
            "scene_seed": self.scene_seed,
            "npc_seed": self.npc_seed,
        }


class DestinationSelector:
    def __init__(self, overpass_provider: OverpassProvider | None = None) -> None:
        self.overpass_provider = overpass_provider or OverpassProvider()

    def select_destinations(
        self,
        *,
        latitude: float | None,
        longitude: float | None,
        radius_meters: int = DEFAULT_SEARCH_RADIUS_METERS,
        location_context: LocationContext | None = None,
    ) -> list[SelectedDestination]:
        if latitude is None or longitude is None:
            logger.info("destination selector fallback | reason=missing_coordinates")
            return [self._build_fallback_destination(category, location_context) for category in ("cafe", "bookstore", "park")]

        category_candidates = {
            category: self._fetch_category_candidates(
                category=category,
                latitude=latitude,
                longitude=longitude,
                radius_meters=radius_meters,
            )
            for category in ("cafe", "bookstore", "park")
        }

        selected_places: list[tuple[str, OverpassPlace]] = []
        used_keys: set[str] = set()
        for category in ("cafe", "bookstore", "park"):
            place = self._choose_best_place(category, category_candidates, used_keys)
            if place is None:
                continue
            selected_places.append((category, place))
            used_keys.add(_place_key(place))

        destinations = [self._build_destination(category, place) for category, place in selected_places]
        for category in ("cafe", "bookstore", "park"):
            if any(destination.category == category for destination in destinations):
                continue
            destinations.append(self._build_fallback_destination(category, location_context))
        ordered = sorted(destinations, key=lambda item: ("cafe", "bookstore", "park").index(item.category))
        logger.info("destination selector complete | destinations=%s", [f"{item.category}:{item.label}" for item in ordered[:3]])
        return ordered[:3]

    def _fetch_category_candidates(
        self,
        *,
        category: str,
        latitude: float,
        longitude: float,
        radius_meters: int,
    ) -> list[OverpassPlace]:
        raw_candidates = self.overpass_provider.search_nearby(
            latitude=latitude,
            longitude=longitude,
            radius_meters=radius_meters,
            tag_filters=CATEGORY_FILTERS[category],
            limit=20,
        )
        deduped: dict[str, OverpassPlace] = {}
        for place in sorted(raw_candidates, key=lambda item: (_score_place(item), item.distance_meters or 999999)):
            deduped.setdefault(_place_key(place), place)
        return list(deduped.values())

    def _choose_best_place(
        self,
        category: str,
        category_candidates: dict[str, list[OverpassPlace]],
        used_keys: set[str],
    ) -> OverpassPlace | None:
        for fallback_category in CATEGORY_FALLBACKS[category]:
            for place in category_candidates.get(fallback_category, []):
                if _place_key(place) in used_keys:
                    continue
                return place
        return None

    def _build_destination(self, category: str, place: OverpassPlace) -> SelectedDestination:
        label = place.name
        distance_text = _format_distance(place.distance_meters)
        description = _build_description(category, label, distance_text, place.tags)
        return SelectedDestination(
            location_id=_build_location_id(category, place),
            category=category,
            label=label,
            description=description,
            place_metadata={
                "name": place.name,
                "display_address": place.display_address,
                "latitude": place.latitude,
                "longitude": place.longitude,
                "osm_type": place.osm_type,
                "osm_id": place.osm_id,
                "distance_meters": place.distance_meters,
                "tags": dict(place.tags),
            },
            scene_seed={
                "category": category,
                "name": place.name,
                "address": place.display_address,
                "distance_text": distance_text,
            },
            npc_seed={
                "category": category,
                "venue_name": place.name,
                "venue_tags": dict(place.tags),
            },
        )

    def _build_fallback_destination(self, category: str, location_context: LocationContext | None) -> SelectedDestination:
        area = " ".join(part for part in [location_context.neighborhood if location_context else "", location_context.city if location_context else ""] if part).strip() or "Nearby"
        fallback_label = {
            "cafe": f"{area} Coffee Stop",
            "bookstore": f"{area} Reading Room",
            "park": f"{area} Green Walk",
        }[category]
        fallback_description = {
            "cafe": "A plausible nearby cafe-style fallback selected when map coverage is thin.",
            "bookstore": "A quiet reading-oriented fallback selected when a bookstore is not clearly available nearby.",
            "park": "An outdoor breathing-space fallback selected when a park or square is not clearly mapped nearby.",
        }[category]
        location_id = f"{category}_{_slugify(fallback_label)}_fallback"
        logger.info("destination selector synthetic fallback | category=%s | label=%s", category, fallback_label)
        return SelectedDestination(
            location_id=location_id,
            category=category,
            label=fallback_label,
            description=fallback_description,
            place_metadata={
                "name": fallback_label,
                "display_address": location_context.formatted_address if location_context else "",
                "latitude": location_context.latitude if location_context else None,
                "longitude": location_context.longitude if location_context else None,
                "fallback": True,
                "tags": {"category": category},
            },
            scene_seed={
                "category": category,
                "name": fallback_label,
                "address": location_context.formatted_address if location_context else "",
                "distance_text": "a short walk away",
            },
            npc_seed={
                "category": category,
                "venue_name": fallback_label,
                "venue_tags": {"fallback": "true"},
            },
        )


def _score_place(place: OverpassPlace) -> tuple[int, float]:
    quality = 0
    if place.tags.get("name"):
        quality += 2
    if place.display_address:
        quality += 1
    if place.tags.get("website") or place.tags.get("phone"):
        quality += 1
    distance = place.distance_meters if place.distance_meters is not None else 999999.0
    return (-quality, distance)


def _place_key(place: OverpassPlace) -> str:
    return "|".join(
        [
            place.name.lower().strip(),
            f"{place.latitude or 0:.5f}",
            f"{place.longitude or 0:.5f}",
        ]
    )


def _build_location_id(category: str, place: OverpassPlace) -> str:
    slug = _slugify(place.name) or category
    digest = sha256(_place_key(place).encode("utf-8")).hexdigest()[:8]
    return f"{category}_{slug}_{digest}"


def _slugify(value: str) -> str:
    return "_".join("".join(ch.lower() if ch.isalnum() else " " for ch in value).split()[:6])


def _format_distance(distance_meters: float | None) -> str:
    if distance_meters is None:
        return "nearby"
    if distance_meters < 1000:
        return f"about {int(round(distance_meters / 10.0) * 10)} meters away"
    return f"about {distance_meters / 1000:.1f} km away"


def _build_description(category: str, label: str, distance_text: str, tags: dict[str, str]) -> str:
    if category == "cafe":
        if tags.get("shop") == "bakery":
            return f"A bakery-style coffee stop at {label}, {distance_text}."
        return f"A nearby cafe option at {label}, {distance_text}."
    if category == "bookstore":
        if tags.get("amenity") == "library":
            return f"A quiet reading-friendly stop at {label}, {distance_text}."
        return f"An independent bookish stop at {label}, {distance_text}."
    return f"An outdoor breather at {label}, {distance_text}."
