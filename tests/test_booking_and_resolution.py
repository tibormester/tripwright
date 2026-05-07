from __future__ import annotations

import unittest
from unittest.mock import patch

from backend.location.booking_parser import extract_lodging_query_from_url, is_booking_url, is_probable_url, parse_booking_page
from backend.location.providers import NominatimPlace
from backend.location.service import LodgingResolutionService
from backend.config import AppConfig


BOOKING_HTML = """
<html>
  <head>
    <title>The Hoxton Williamsburg - Booking.com</title>
    <link rel=\"canonical\" href=\"https://www.booking.com/hotel/us/the-hoxton-williamsburg.html\" />
    <script type=\"application/ld+json\">
      {
        \"@context\": \"https://schema.org\",
        \"@type\": \"Hotel\",
        \"name\": \"The Hoxton Williamsburg\",
        \"address\": {
          \"@type\": \"PostalAddress\",
          \"streetAddress\": \"97 Wythe Ave\",
          \"addressLocality\": \"Brooklyn\",
          \"addressRegion\": \"NY\",
          \"postalCode\": \"11249\",
          \"addressCountry\": \"United States\"
        },
        \"geo\": {\"@type\": \"GeoCoordinates\", \"latitude\": 40.7216, \"longitude\": -73.9582}
      }
    </script>
  </head>
  <body></body>
</html>
"""


class FakeNominatimProvider:
    def geocode(self, query: str) -> NominatimPlace | None:
        self.last_query = query
        self.queries = getattr(self, "queries", []) + [query]
        return NominatimPlace(
            display_name="The Hoxton Williamsburg, 97 Wythe Ave, Brooklyn, New York, United States",
            latitude=40.7216,
            longitude=-73.9582,
            name="The Hoxton Williamsburg",
            city="Brooklyn",
            neighborhood="Williamsburg",
            region="New York",
            country="United States",
            osm_type="way",
            osm_id="12345",
            raw_payload={"mock": True},
        )


class BookingAndResolutionTests(unittest.TestCase):
    def test_booking_parser_extracts_core_fields(self) -> None:
        parsed = parse_booking_page(BOOKING_HTML)

        self.assertEqual(parsed.name, "The Hoxton Williamsburg")
        self.assertEqual(parsed.city, "Brooklyn")
        self.assertEqual(parsed.latitude, 40.7216)
        self.assertEqual(parsed.longitude, -73.9582)

    def test_url_helpers(self) -> None:
        self.assertTrue(is_probable_url("https://example.com/hotel"))
        self.assertTrue(is_booking_url("https://www.booking.com/hotel/us/demo.html"))
        self.assertFalse(is_booking_url("https://example.com/hotel"))
        self.assertEqual(
            extract_lodging_query_from_url("https://www.booking.com/hotel/us/the-hoxton-williamsburg.html?label=abc123xyz"),
            "the hoxton williamsburg",
        )

    def test_lodging_resolution_falls_back_to_geocoding(self) -> None:
        provider = FakeNominatimProvider()
        service = LodgingResolutionService(
            AppConfig(booking_fetch_enabled=False, geocoding_enabled=True),
            nominatim_provider=provider,
        )

        result = service.resolve("The Hoxton Williamsburg")

        self.assertEqual(result.location_context.canonical_name, "The Hoxton Williamsburg")
        self.assertEqual(result.location_context.provider, "nominatim")
        self.assertEqual(result.location_context.provider_place_id, "way:12345")
        self.assertIn("Hoxton", provider.last_query)

    def test_booking_url_resolution_uses_booking_metadata(self) -> None:
        provider = FakeNominatimProvider()
        service = LodgingResolutionService(
            AppConfig(booking_fetch_enabled=True, geocoding_enabled=True),
            nominatim_provider=provider,
        )

        with patch("backend.location.service.fetch_booking_page", return_value=BOOKING_HTML):
            result = service.resolve("https://www.booking.com/hotel/us/the-hoxton-williamsburg.html")

        self.assertEqual(result.location_context.input_kind, "booking_url")
        self.assertEqual(result.location_context.canonical_name, "The Hoxton Williamsburg")
        self.assertEqual(result.booking_metadata.name, "The Hoxton Williamsburg")

    def test_booking_url_resolution_uses_url_slug_when_fetch_fails(self) -> None:
        provider = FakeNominatimProvider()
        service = LodgingResolutionService(
            AppConfig(booking_fetch_enabled=True, geocoding_enabled=True),
            nominatim_provider=provider,
        )

        with patch("backend.location.service.fetch_booking_page", side_effect=RuntimeError("blocked")):
            result = service.resolve("https://www.booking.com/hotel/us/the-hoxton-williamsburg.html?label=abc123xyz")

        self.assertEqual(provider.last_query, "the hoxton williamsburg")
        self.assertEqual(result.location_context.canonical_name, "The Hoxton Williamsburg")


class QueryVariantProvider:
    def __init__(self) -> None:
        self.queries: list[str] = []

    def geocode(self, query: str) -> NominatimPlace | None:
        self.queries.append(query)
        if query == "97 Wythe Ave, Brooklyn":
            return NominatimPlace(
                display_name="97 Wythe Ave, Brooklyn, New York, United States",
                latitude=40.7216,
                longitude=-73.9582,
                name="97 Wythe Ave",
                city="Brooklyn",
                neighborhood="Williamsburg",
                region="New York",
                country="United States",
                osm_type="way",
                osm_id="12345",
                raw_payload={"mock": True},
            )
        return None


class ProviderParsingTests(unittest.TestCase):
    def test_nominatim_provider_uses_bounding_box_center_when_needed(self) -> None:
        from backend.location.providers import _bounding_box_center, _pick_best_nominatim_item

        self.assertEqual(_bounding_box_center(["40.0", "42.0", "-74.0", "-72.0"]), (41.0, -73.0))
        chosen = _pick_best_nominatim_item(
            [
                {"display_name": "Weak Result", "address": {}, "boundingbox": ["40.0", "42.0", "-74.0", "-72.0"]},
                {"display_name": "Strong Result", "lat": "40.7216", "lon": "-73.9582", "address": {"city": "Brooklyn", "country": "United States"}},
            ]
        )
        self.assertEqual(chosen["display_name"], "Strong Result")

    def test_resolution_tries_multiple_geocode_queries_for_addresses(self) -> None:
        provider = QueryVariantProvider()
        service = LodgingResolutionService(
            AppConfig(booking_fetch_enabled=False, geocoding_enabled=True),
            nominatim_provider=provider,
        )

        result = service.resolve("97 Wythe Ave, Brooklyn, NY 11249, United States")

        self.assertEqual(result.location_context.latitude, 40.7216)
        self.assertIn("97 Wythe Ave, Brooklyn", provider.queries)


if __name__ == "__main__":
    unittest.main()
