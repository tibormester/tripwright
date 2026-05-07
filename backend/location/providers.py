from __future__ import annotations

from dataclasses import dataclass
import logging
from math import atan2, cos, radians, sin, sqrt
import time
from typing import Any

logger = logging.getLogger(__name__)

NOMINATIM_BASE_URL = "https://nominatim.openstreetmap.org/search"
OVERPASS_BASE_URL = "https://overpass-api.de/api/interpreter"
DEFAULT_USER_AGENT = "tripwright/0.1 (dynamic-world prototype)"


@dataclass
class NominatimPlace:
    display_name: str
    latitude: float | None
    longitude: float | None
    name: str
    city: str
    neighborhood: str
    region: str
    country: str
    osm_type: str
    osm_id: str
    raw_payload: dict[str, Any]


@dataclass
class OverpassPlace:
    osm_type: str
    osm_id: str
    name: str
    latitude: float | None
    longitude: float | None
    tags: dict[str, str]
    display_address: str
    distance_meters: float | None
    raw_payload: dict[str, Any]


class NominatimProvider:
    def __init__(self, *, timeout_seconds: float = 10.0, user_agent: str = DEFAULT_USER_AGENT, max_retries: int = 0) -> None:
        self.timeout_seconds = timeout_seconds
        self.user_agent = user_agent
        self.max_retries = max_retries

    def geocode(self, query: str) -> NominatimPlace | None:
        cleaned_query = query.strip()
        if not cleaned_query:
            return None

        import requests

        last_error: Exception | None = None
        payload = None
        for attempt in range(self.max_retries + 1):
            try:
                response = requests.get(
                    NOMINATIM_BASE_URL,
                    timeout=self.timeout_seconds,
                    headers={"User-Agent": self.user_agent},
                    params={
                        "q": cleaned_query,
                        "format": "jsonv2",
                        "limit": 1,
                        "addressdetails": 1,
                    },
                )
                response.raise_for_status()
                payload = response.json()
                if attempt:
                    logger.info("nominatim geocode recovered | query=%s | attempt=%s", cleaned_query, attempt + 1)
                break
            except Exception as exc:
                last_error = exc
                logger.warning("nominatim geocode failed | query=%s | attempt=%s/%s | error=%s", cleaned_query, attempt + 1, self.max_retries + 1, exc)
                if attempt < self.max_retries:
                    time.sleep(min(0.5 * (attempt + 1), 1.5))
        if payload is None:
            if last_error is not None:
                raise last_error
            return None
        if not isinstance(payload, list) or not payload:
            return None

        item = payload[0]
        if not isinstance(item, dict):
            return None

        address = item.get("address") if isinstance(item.get("address"), dict) else {}
        place_name = _extract_place_name(item, address)

        return NominatimPlace(
            display_name=str(item.get("display_name", "")),
            latitude=_to_float(item.get("lat")),
            longitude=_to_float(item.get("lon")),
            name=place_name,
            city=_first_non_empty(address.get("city"), address.get("town"), address.get("village"), address.get("municipality")),
            neighborhood=_first_non_empty(
                address.get("neighbourhood"),
                address.get("suburb"),
                address.get("quarter"),
                address.get("city_district"),
            ),
            region=_first_non_empty(address.get("state"), address.get("region"), address.get("county")),
            country=_first_non_empty(address.get("country")),
            osm_type=str(item.get("osm_type", "")),
            osm_id=str(item.get("osm_id", "")),
            raw_payload=item,
        )


class OverpassProvider:
    def __init__(self, *, timeout_seconds: float = 15.0, user_agent: str = DEFAULT_USER_AGENT, max_retries: int = 0) -> None:
        self.timeout_seconds = timeout_seconds
        self.user_agent = user_agent
        self.max_retries = max_retries

    def search_nearby(
        self,
        *,
        latitude: float,
        longitude: float,
        radius_meters: int,
        tag_filters: list[tuple[str, str]],
        limit: int = 12,
    ) -> list[OverpassPlace]:
        if not tag_filters:
            return []

        query = self._build_query(
            latitude=latitude,
            longitude=longitude,
            radius_meters=radius_meters,
            tag_filters=tag_filters,
            limit=limit,
        )

        import requests

        last_error: Exception | None = None
        payload = None
        for attempt in range(self.max_retries + 1):
            try:
                response = requests.post(
                    OVERPASS_BASE_URL,
                    timeout=self.timeout_seconds,
                    headers={"User-Agent": self.user_agent},
                    data=query.encode("utf-8"),
                )
                response.raise_for_status()
                payload = response.json()
                if attempt:
                    logger.info("overpass search recovered | attempt=%s | radius=%s", attempt + 1, radius_meters)
                break
            except Exception as exc:
                last_error = exc
                logger.warning("overpass search failed | attempt=%s/%s | radius=%s | error=%s", attempt + 1, self.max_retries + 1, radius_meters, exc)
                if attempt < self.max_retries:
                    time.sleep(min(0.5 * (attempt + 1), 1.5))
        if payload is None:
            if last_error is not None:
                raise last_error
            return []
        elements = payload.get("elements", []) if isinstance(payload, dict) else []

        places: list[OverpassPlace] = []
        for element in elements:
            if not isinstance(element, dict):
                continue
            place = _normalize_overpass_place(element, origin_latitude=latitude, origin_longitude=longitude)
            if place is not None:
                places.append(place)
        return places

    def _build_query(
        self,
        *,
        latitude: float,
        longitude: float,
        radius_meters: int,
        tag_filters: list[tuple[str, str]],
        limit: int,
    ) -> str:
        filter_lines = []
        for tag_key, tag_value in tag_filters:
            escaped_key = tag_key.replace('"', '\\"')
            escaped_value = tag_value.replace('"', '\\"')
            filter_lines.extend(
                [
                    f'  node["{escaped_key}"="{escaped_value}"](around:{radius_meters},{latitude},{longitude});',
                    f'  way["{escaped_key}"="{escaped_value}"](around:{radius_meters},{latitude},{longitude});',
                    f'  relation["{escaped_key}"="{escaped_value}"](around:{radius_meters},{latitude},{longitude});',
                ]
            )

        return (
            "[out:json][timeout:25];\n(\n"
            + "\n".join(filter_lines)
            + f"\n);\nout center {limit};"
        )


def _normalize_overpass_place(
    element: dict[str, Any],
    *,
    origin_latitude: float,
    origin_longitude: float,
) -> OverpassPlace | None:
    tags = element.get("tags") if isinstance(element.get("tags"), dict) else {}
    latitude = _to_float(element.get("lat"))
    longitude = _to_float(element.get("lon"))

    center = element.get("center") if isinstance(element.get("center"), dict) else {}
    if latitude is None:
        latitude = _to_float(center.get("lat"))
    if longitude is None:
        longitude = _to_float(center.get("lon"))

    name = _first_non_empty(tags.get("name"), tags.get("brand"), tags.get("operator"))
    if not name:
        return None

    return OverpassPlace(
        osm_type=str(element.get("type", "")),
        osm_id=str(element.get("id", "")),
        name=name,
        latitude=latitude,
        longitude=longitude,
        tags={str(key): str(value) for key, value in tags.items()},
        display_address=_build_display_address(tags),
        distance_meters=_haversine_distance_meters(origin_latitude, origin_longitude, latitude, longitude),
        raw_payload=element,
    )


def _build_display_address(tags: dict[str, Any]) -> str:
    house_number = str(tags.get("addr:housenumber", "")).strip()
    street = str(tags.get("addr:street", "")).strip()
    city = str(tags.get("addr:city", "")).strip()
    parts = []
    street_line = " ".join(part for part in [house_number, street] if part)
    if street_line:
        parts.append(street_line)
    if city:
        parts.append(city)
    return ", ".join(parts)


def _extract_place_name(item: dict[str, Any], address: dict[str, Any]) -> str:
    return _first_non_empty(
        item.get("name"),
        address.get("hotel"),
        address.get("tourism"),
        address.get("attraction"),
        address.get("building"),
        str(item.get("display_name", "")).split(",", 1)[0],
    )


def _first_non_empty(*values: Any) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def _to_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _haversine_distance_meters(
    latitude_1: float,
    longitude_1: float,
    latitude_2: float | None,
    longitude_2: float | None,
) -> float | None:
    if latitude_2 is None or longitude_2 is None:
        return None

    earth_radius_m = 6_371_000
    phi_1 = radians(latitude_1)
    phi_2 = radians(latitude_2)
    delta_phi = radians(latitude_2 - latitude_1)
    delta_lambda = radians(longitude_2 - longitude_1)

    a = sin(delta_phi / 2) ** 2 + cos(phi_1) * cos(phi_2) * sin(delta_lambda / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return earth_radius_m * c
