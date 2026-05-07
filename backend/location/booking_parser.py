from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import unquote, urlparse

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

BOOKING_HOSTS = {"booking.com", "www.booking.com"}
BOOKING_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


@dataclass
class BookingPageMetadata:
    name: str = ""
    address: str = ""
    latitude: float | None = None
    longitude: float | None = None
    city: str = ""
    neighborhood: str = ""
    region: str = ""
    country: str = ""
    canonical_url: str | None = None
    lodging_type_hint: str = "unknown"
    raw_metadata: dict[str, Any] = field(default_factory=dict)

    def build_query(self) -> str:
        parts = [self.name, self.address, self.city, self.region, self.country]
        return ", ".join(part.strip() for part in parts if part and part.strip())

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "address": self.address,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "city": self.city,
            "neighborhood": self.neighborhood,
            "region": self.region,
            "country": self.country,
            "canonical_url": self.canonical_url,
            "lodging_type_hint": self.lodging_type_hint,
            "raw_metadata": self.raw_metadata,
        }


def is_probable_url(value: str) -> bool:
    parsed = urlparse((value or "").strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def is_booking_url(value: str) -> bool:
    parsed = urlparse((value or "").strip())
    hostname = (parsed.hostname or "").lower()
    return hostname in BOOKING_HOSTS or hostname.endswith(".booking.com")


def extract_lodging_query_from_url(value: str) -> str:
    parsed = urlparse((value or "").strip())
    path_parts = [part for part in parsed.path.split("/") if part]
    if not path_parts:
        return ""

    candidate = path_parts[-1]
    candidate = unquote(candidate)
    candidate = re.sub(r"\.[a-zA-Z0-9]+$", "", candidate)
    candidate = re.sub(r"^[a-z]{2}(?:-[a-z]{2})?-", "", candidate)
    candidate = re.sub(r"[-_]+", " ", candidate)
    candidate = re.sub(r"\s+", " ", candidate).strip()

    ignored = {"hotel", "hotels", "searchresults", "index", "share"}
    if candidate.lower() in ignored:
        return ""
    return candidate


def fetch_booking_page(url: str, timeout_seconds: float = 10.0, max_retries: int = 0) -> str:
    import requests

    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            response = requests.get(
                url,
                timeout=timeout_seconds,
                headers={
                    "User-Agent": BOOKING_USER_AGENT,
                    "Accept-Language": "en-US,en;q=0.9",
                },
            )
            response.raise_for_status()
            if attempt:
                logger.info("booking fetch recovered | url=%s | attempt=%s", url, attempt + 1)
            return response.text
        except Exception as exc:
            last_error = exc
            logger.warning("booking fetch failed | url=%s | attempt=%s/%s | error=%s", url, attempt + 1, max_retries + 1, exc)
            if attempt < max_retries:
                time.sleep(min(0.5 * (attempt + 1), 1.5))
    assert last_error is not None
    raise last_error


def parse_booking_page(html: str, source_url: str | None = None) -> BookingPageMetadata:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    metadata = BookingPageMetadata(canonical_url=source_url)

    canonical_link = soup.find("link", attrs={"rel": lambda value: value and "canonical" in value})
    if canonical_link and canonical_link.get("href"):
        metadata.canonical_url = canonical_link.get("href").strip()

    json_ld_items = _extract_json_ld_items(soup)
    for item in json_ld_items:
        _merge_json_ld_item(metadata, item)

    og_title = _get_meta_content(soup, "property", "og:title") or _get_meta_content(soup, "name", "title")
    if not metadata.name and og_title:
        metadata.name = _clean_name(og_title)

    if not metadata.name and soup.title and soup.title.string:
        metadata.name = _clean_name(soup.title.string)

    og_url = _get_meta_content(soup, "property", "og:url")
    if og_url and not metadata.canonical_url:
        metadata.canonical_url = og_url.strip()

    extracted_coordinates = _extract_coordinates_from_text(html)
    if metadata.latitude is None and extracted_coordinates[0] is not None:
        metadata.latitude = extracted_coordinates[0]
    if metadata.longitude is None and extracted_coordinates[1] is not None:
        metadata.longitude = extracted_coordinates[1]

    if not metadata.address:
        metadata.address = _extract_address_candidate(soup)

    _fill_location_parts_from_address(metadata)
    metadata.lodging_type_hint = infer_lodging_type_hint(metadata.name, metadata.address)
    metadata.raw_metadata = {
        "json_ld_count": len(json_ld_items),
        "title": soup.title.string.strip() if soup.title and soup.title.string else "",
        "canonical_url": metadata.canonical_url,
    }
    return metadata


def infer_lodging_type_hint(*values: str) -> str:
    haystack = " ".join(value.lower() for value in values if value)
    if any(keyword in haystack for keyword in {"hostel", "hotel", "resort", "suite"}):
        return "hotel"
    if any(keyword in haystack for keyword in {"guesthouse", "guest house", "inn", "b&b", "bed and breakfast"}):
        return "guesthouse"
    if any(keyword in haystack for keyword in {"apartment", "villa", "loft", "home", "airbnb", "rental", "residence"}):
        return "apartment"
    return "unknown"


def _extract_json_ld_items(soup: BeautifulSoup) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw_text = script.string or script.get_text() or ""
        raw_text = raw_text.strip()
        if not raw_text:
            continue
        try:
            payload = json.loads(raw_text)
        except json.JSONDecodeError:
            continue
        items.extend(_flatten_json_ld_payload(payload))
    return items


def _flatten_json_ld_payload(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        if isinstance(payload.get("@graph"), list):
            items: list[dict[str, Any]] = []
            for item in payload["@graph"]:
                items.extend(_flatten_json_ld_payload(item))
            return items
        return [payload]
    if isinstance(payload, list):
        items: list[dict[str, Any]] = []
        for item in payload:
            items.extend(_flatten_json_ld_payload(item))
        return items
    return []


def _merge_json_ld_item(metadata: BookingPageMetadata, item: dict[str, Any]) -> None:
    item_type = str(item.get("@type", ""))
    if not any(token in item_type.lower() for token in {"hotel", "lodgingbusiness", "apartment", "hostel", "resort", "place"}):
        return

    if not metadata.name and item.get("name"):
        metadata.name = str(item.get("name", "")).strip()

    address = item.get("address")
    if isinstance(address, dict):
        if not metadata.address:
            metadata.address = _join_address_parts(
                address.get("streetAddress"),
                address.get("addressLocality"),
                address.get("addressRegion"),
                address.get("postalCode"),
                address.get("addressCountry"),
            )
        metadata.city = metadata.city or str(address.get("addressLocality", "")).strip()
        metadata.region = metadata.region or str(address.get("addressRegion", "")).strip()
        metadata.country = metadata.country or str(address.get("addressCountry", "")).strip()

    geo = item.get("geo")
    if isinstance(geo, dict):
        if metadata.latitude is None:
            metadata.latitude = _to_float(geo.get("latitude"))
        if metadata.longitude is None:
            metadata.longitude = _to_float(geo.get("longitude"))

    if not metadata.canonical_url and item.get("url"):
        metadata.canonical_url = str(item.get("url", "")).strip()


def _get_meta_content(soup: BeautifulSoup, attr_name: str, attr_value: str) -> str | None:
    tag = soup.find("meta", attrs={attr_name: attr_value})
    if tag and tag.get("content"):
        return str(tag.get("content")).strip()
    return None


def _extract_coordinates_from_text(html: str) -> tuple[float | None, float | None]:
    latitude_match = re.search(r'"latitude"\s*[:=]\s*"?(-?\d+\.\d+)"?', html, re.IGNORECASE)
    longitude_match = re.search(r'"longitude"\s*[:=]\s*"?(-?\d+\.\d+)"?', html, re.IGNORECASE)
    if latitude_match and longitude_match:
        return _to_float(latitude_match.group(1)), _to_float(longitude_match.group(1))

    center_match = re.search(
        r"(?:b_map_center_latitude|map_center_latitude)\s*[:=]\s*'?(-?\d+\.\d+).*?(?:b_map_center_longitude|map_center_longitude)\s*[:=]\s*'?(-?\d+\.\d+)",
        html,
        re.IGNORECASE | re.DOTALL,
    )
    if center_match:
        return _to_float(center_match.group(1)), _to_float(center_match.group(2))

    return None, None


def _extract_address_candidate(soup: BeautifulSoup) -> str:
    selectors = [
        {"data-testid": "PropertyHeaderAddressDesktop"},
        {"data-testid": "PropertyHeaderAddress"},
        {"class": re.compile("address", re.IGNORECASE)},
    ]
    for attrs in selectors:
        node = soup.find(attrs=attrs)
        if node:
            text = " ".join(node.stripped_strings)
            if text:
                return text.strip()
    return ""


def _fill_location_parts_from_address(metadata: BookingPageMetadata) -> None:
    if not metadata.address:
        return

    parts = [part.strip() for part in metadata.address.split(",") if part.strip()]
    if not metadata.country and len(parts) >= 1:
        metadata.country = parts[-1]
    if not metadata.region and len(parts) >= 2:
        metadata.region = parts[-2]
    if not metadata.city and len(parts) >= 3:
        metadata.city = parts[-3]
    if not metadata.neighborhood and len(parts) >= 4:
        metadata.neighborhood = parts[-4]


def _join_address_parts(*parts: Any) -> str:
    return ", ".join(str(part).strip() for part in parts if part and str(part).strip())


def _clean_name(value: str) -> str:
    cleaned = value.split("|", 1)[0].split("- Booking", 1)[0].strip()
    return cleaned


def _to_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None
