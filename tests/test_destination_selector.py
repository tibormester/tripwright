from __future__ import annotations

import unittest

from backend.location.destination_selector import DestinationSelector
from backend.location.models import LocationContext
from backend.location.providers import OverpassPlace


class FakeOverpassProvider:
    def search_nearby(self, **kwargs):
        tag_filters = kwargs["tag_filters"]
        if ("amenity", "cafe") in tag_filters or ("shop", "bakery") in tag_filters:
            return [OverpassPlace("node", "1", "Daybreak Cafe", 40.0, -73.0, {"name": "Daybreak Cafe", "amenity": "cafe"}, "12 Main St", 120.0, {})]
        if ("shop", "books") in tag_filters:
            return []
        return [OverpassPlace("node", "3", "Riverfront Square", 40.0, -73.0, {"name": "Riverfront Square", "place": "square"}, "River Rd", 450.0, {})]


class DestinationSelectorTests(unittest.TestCase):
    def test_selector_returns_exactly_three_destinations(self) -> None:
        selector = DestinationSelector(FakeOverpassProvider())
        context = LocationContext(
            input_value="The Hoxton Williamsburg",
            input_kind="lodging_query",
            canonical_name="The Hoxton Williamsburg",
            formatted_address="97 Wythe Ave, Brooklyn, NY 11249, United States",
            latitude=40.7216,
            longitude=-73.9582,
            city="Brooklyn",
            neighborhood="Williamsburg",
        )

        destinations = selector.select_destinations(
            latitude=context.latitude,
            longitude=context.longitude,
            location_context=context,
        )

        self.assertEqual(len(destinations), 3)
        self.assertEqual([item.category for item in destinations], ["cafe", "bookstore", "park"])
        self.assertEqual(destinations[0].label, "Daybreak Cafe")
        self.assertTrue(destinations[1].location_id.endswith("fallback"))


if __name__ == "__main__":
    unittest.main()
