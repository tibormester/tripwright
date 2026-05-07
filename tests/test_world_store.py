from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backend.location.models import LocationContext
from backend.research.models import ResearchReport
from backend.world_state import RuntimeSceneDefinition, WorldState
from backend.world_store import FileWorldStore, MemoryWorldStore, build_canonical_lodging_fingerprint, generate_world_id


class WorldStoreTests(unittest.TestCase):
    def _build_location(self) -> LocationContext:
        return LocationContext(
            input_value="The Hoxton Williamsburg",
            input_kind="lodging_query",
            canonical_name="The Hoxton Williamsburg",
            formatted_address="97 Wythe Ave, Brooklyn, NY 11249, United States",
            latitude=40.72161,
            longitude=-73.95824,
            city="Brooklyn",
            region="New York",
            country="United States",
        )

    def _build_world(self) -> WorldState:
        location = self._build_location()
        scene = RuntimeSceneDefinition(
            location_id="lodging",
            category="lodging",
            label="The Hoxton Williamsburg",
            description="Arrive and get oriented.",
            location="the lobby of The Hoxton Williamsburg",
            narrator_text="You arrive.",
        )
        return WorldState(
            world_id=generate_world_id(),
            created_at="2026-05-06T12:00:00+00:00",
            fingerprint=build_canonical_lodging_fingerprint(location),
            location_context=location,
            research_report=ResearchReport(area_summary="Walkable and creative."),
            lodging_scene=scene,
        )

    def test_fingerprint_is_stable(self) -> None:
        location_a = self._build_location()
        location_b = self._build_location()
        location_b.latitude = 40.72162
        location_b.longitude = -73.95823

        self.assertEqual(
            build_canonical_lodging_fingerprint(location_a),
            build_canonical_lodging_fingerprint(location_b),
        )

    def test_memory_store_round_trip(self) -> None:
        world = self._build_world()
        store = MemoryWorldStore()

        store.save_fingerprint_mapping(world.fingerprint, world.world_id)
        store.save_world(world)

        self.assertEqual(store.find_world_id_by_fingerprint(world.fingerprint), world.world_id)
        self.assertEqual(store.get_world(world.world_id).world_id, world.world_id)

    def test_file_store_round_trip(self) -> None:
        world = self._build_world()
        with tempfile.TemporaryDirectory() as temp_dir:
            store = FileWorldStore(Path(temp_dir))
            store.save_fingerprint_mapping(world.fingerprint, world.world_id)
            store.save_world(world)

            self.assertEqual(store.find_world_id_by_fingerprint(world.fingerprint), world.world_id)
            loaded = store.get_world(world.world_id)
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.location_context.canonical_name, world.location_context.canonical_name)


if __name__ == "__main__":
    unittest.main()
