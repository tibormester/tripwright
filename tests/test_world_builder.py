from __future__ import annotations

import unittest

from backend.location.destination_selector import SelectedDestination
from backend.location.models import LocationContext
from backend.research.models import ResearchReport
from backend.world_builder import WorldBuilder


class WorldBuilderTests(unittest.TestCase):
    def test_world_builder_creates_lodging_scene_and_lazy_destination_seeds(self) -> None:
        builder = WorldBuilder()
        location = LocationContext(
            input_value="The Hoxton Williamsburg",
            input_kind="lodging_query",
            canonical_name="The Hoxton Williamsburg",
            formatted_address="97 Wythe Ave, Brooklyn, NY 11249, United States",
            latitude=40.7216,
            longitude=-73.9582,
            city="Brooklyn",
            neighborhood="Williamsburg",
            lodging_type="hotel",
        )
        research = ResearchReport(
            area_summary="Creative waterfront blocks with coffee, books, and short walks.",
            tone_keywords=["creative", "walkable", "waterfront"],
            destination_recommendation_notes=["Short neighborhood stops work well here."],
        )
        destinations = [
            SelectedDestination("cafe_daybreak", "cafe", "Daybreak Cafe", "Cafe nearby", {}, {"category": "cafe"}, {"category": "cafe"}),
            SelectedDestination("book_paper", "bookstore", "Paper Lantern Books", "Books nearby", {}, {"category": "bookstore"}, {"category": "bookstore"}),
            SelectedDestination("park_river", "park", "Riverfront Square", "Park nearby", {}, {"category": "park"}, {"category": "park"}),
        ]

        world = builder.build_world(location_context=location, research_report=research, destinations=destinations)
        conversation = builder.build_initial_conversation(world)

        self.assertEqual(world.lodging_scene.label, "The Hoxton Williamsburg")
        self.assertEqual(len(world.travel_scenes), 3)
        self.assertIsNotNone(world.lodging_scene.npc_profile)
        self.assertEqual(conversation.scene_label, world.lodging_scene.label)
        self.assertIn("research_report", conversation.system_context)
        self.assertEqual(len(conversation.available_travel_options), 3)

        generated_scene = builder.ensure_destination_generated(world, "cafe_daybreak")
        self.assertIsNotNone(generated_scene.npc_profile)
        self.assertIn("cafe_daybreak", world.generated_scene_cache)
        self.assertIn("cafe_daybreak", world.generated_npc_cache)


if __name__ == "__main__":
    unittest.main()
