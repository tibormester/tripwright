from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any

from ..config import AppConfig
from .booking_parser import (
    BookingPageMetadata,
    extract_lodging_query_from_url,
    fetch_booking_page,
    infer_lodging_type_hint,
    is_booking_url,
    is_probable_url,
    parse_booking_page,
)
from .models import LocationContext
from .providers import NominatimPlace, NominatimProvider

logger = logging.getLogger(__name__)


@dataclass
class ResolutionResult:
    location_context: LocationContext
    booking_metadata: BookingPageMetadata | None = None
    geocoded_place: NominatimPlace | None = None


class LodgingResolutionService:
    def __init__(self, config: AppConfig | None = None, *, nominatim_provider: NominatimProvider | None = None) -> None:
        self.config = config or AppConfig.from_env()
        self.nominatim_provider = nominatim_provider or NominatimProvider(
            timeout_seconds=self.config.provider_timeout_seconds,
            max_retries=self.config.provider_max_retries,
        )

    def resolve(self, lodging_input: str) -> ResolutionResult:
        cleaned_input = (lodging_input or "").strip()
        if not cleaned_input:
            raise ValueError("lodging_input is required")

        booking_metadata: BookingPageMetadata | None = None
        geocoded_place: NominatimPlace | None = None
        input_kind = self._infer_input_kind(cleaned_input)

        logger.info("lodging resolution start | input_kind=%s | input=%s", input_kind, cleaned_input)

        if input_kind == "booking_url" and self.config.booking_fetch_enabled:
            booking_metadata = self._try_parse_booking_page(cleaned_input)

        geocode_query = self._build_geocode_query(cleaned_input, booking_metadata)
        if self.config.geocoding_enabled:
            geocoded_place = self.nominatim_provider.geocode(geocode_query)

        location_context = self._build_location_context(
            lodging_input=cleaned_input,
            input_kind=input_kind,
            booking_metadata=booking_metadata,
            geocoded_place=geocoded_place,
        )

        if not location_context.canonical_name and not location_context.formatted_address:
            raise ValueError("Unable to resolve lodging input into a canonical location")

        logger.info(
            "lodging resolution complete | provider=%s | confidence=%.2f | canonical_name=%s | city=%s | neighborhood=%s",
            location_context.provider,
            location_context.resolution_confidence,
            location_context.canonical_name,
            location_context.city,
            location_context.neighborhood,
        )
        return ResolutionResult(
            location_context=location_context,
            booking_metadata=booking_metadata,
            geocoded_place=geocoded_place,
        )

    def _infer_input_kind(self, value: str) -> str:
        if is_booking_url(value):
            return "booking_url"
        if is_probable_url(value):
            return "url"
        return "lodging_query"

    def _try_parse_booking_page(self, url: str) -> BookingPageMetadata | None:
        try:
            html = fetch_booking_page(
                url,
                timeout_seconds=self.config.provider_timeout_seconds,
                max_retries=self.config.provider_max_retries,
            )
        except Exception as exc:
            logger.warning("booking parse fetch failed | url=%s | error=%s", url, exc)
            return None
        try:
            metadata = parse_booking_page(html, source_url=url)
            logger.info(
                "booking parse success | url=%s | name=%s | has_address=%s | has_coordinates=%s",
                url,
                metadata.name,
                bool(metadata.address),
                metadata.latitude is not None and metadata.longitude is not None,
            )
            return metadata
        except Exception as exc:
            logger.warning("booking parse failed | url=%s | error=%s", url, exc)
            return None

    def _build_geocode_query(self, lodging_input: str, booking_metadata: BookingPageMetadata | None) -> str:
        if booking_metadata:
            query = booking_metadata.build_query().strip()
            if query:
                return query

        if is_probable_url(lodging_input):
            extracted_query = extract_lodging_query_from_url(lodging_input)
            if extracted_query:
                return extracted_query

        return lodging_input

    def _build_location_context(
        self,
        *,
        lodging_input: str,
        input_kind: str,
        booking_metadata: BookingPageMetadata | None,
        geocoded_place: NominatimPlace | None,
    ) -> LocationContext:
        source_url = booking_metadata.canonical_url if booking_metadata and booking_metadata.canonical_url else None
        canonical_name = _first_non_empty(
            geocoded_place.name if geocoded_place else "",
            booking_metadata.name if booking_metadata else "",
            extract_lodging_query_from_url(lodging_input) if input_kind in {"booking_url", "url"} else "",
            lodging_input,
        )
        formatted_address = _first_non_empty(
            geocoded_place.display_name if geocoded_place else "",
            booking_metadata.address if booking_metadata else "",
        )
        latitude = _first_non_null(
            geocoded_place.latitude if geocoded_place else None,
            booking_metadata.latitude if booking_metadata else None,
        )
        longitude = _first_non_null(
            geocoded_place.longitude if geocoded_place else None,
            booking_metadata.longitude if booking_metadata else None,
        )
        city = _first_non_empty(
            geocoded_place.city if geocoded_place else "",
            booking_metadata.city if booking_metadata else "",
        )
        neighborhood = _first_non_empty(
            geocoded_place.neighborhood if geocoded_place else "",
            booking_metadata.neighborhood if booking_metadata else "",
        )
        region = _first_non_empty(
            geocoded_place.region if geocoded_place else "",
            booking_metadata.region if booking_metadata else "",
        )
        country = _first_non_empty(
            geocoded_place.country if geocoded_place else "",
            booking_metadata.country if booking_metadata else "",
        )

        lodging_type = infer_lodging_type_hint(
            canonical_name,
            formatted_address,
            booking_metadata.lodging_type_hint if booking_metadata else "",
        )

        return LocationContext(
            input_value=lodging_input,
            input_kind=input_kind,
            source_url=source_url,
            canonical_name=canonical_name,
            formatted_address=formatted_address,
            latitude=latitude,
            longitude=longitude,
            city=city,
            neighborhood=neighborhood,
            region=region,
            country=country,
            lodging_type=lodging_type,
            provider="nominatim" if geocoded_place else "booking_html",
            provider_place_id=_build_provider_place_id(geocoded_place),
            resolution_confidence=self._score_confidence(booking_metadata, geocoded_place),
            raw_metadata={
                "booking_metadata": booking_metadata.to_dict() if booking_metadata else None,
                "geocoded_place": geocoded_place.raw_payload if geocoded_place else None,
            },
        )

    def _score_confidence(
        self,
        booking_metadata: BookingPageMetadata | None,
        geocoded_place: NominatimPlace | None,
    ) -> float:
        score = 0.2
        if booking_metadata and booking_metadata.name:
            score += 0.15
        if booking_metadata and booking_metadata.address:
            score += 0.1
        if booking_metadata and booking_metadata.latitude is not None and booking_metadata.longitude is not None:
            score += 0.1
        if geocoded_place:
            score += 0.25
        if geocoded_place and geocoded_place.latitude is not None and geocoded_place.longitude is not None:
            score += 0.1
        if geocoded_place and geocoded_place.city:
            score += 0.05
        if geocoded_place and geocoded_place.country:
            score += 0.05
        return min(score, 0.95)


def _build_provider_place_id(place: NominatimPlace | None) -> str:
    if not place:
        return ""
    if place.osm_type and place.osm_id:
        return f"{place.osm_type}:{place.osm_id}"
    return ""


def _first_non_empty(*values: Any) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def _first_non_null(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None
