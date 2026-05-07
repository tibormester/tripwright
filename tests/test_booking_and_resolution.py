from __future__ import annotations

import unittest
from unittest.mock import patch

from backend.location.booking_parser import is_booking_url, is_probable_url, parse_booking_page
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


if __name__ == "__main__":
    unittest.main()
