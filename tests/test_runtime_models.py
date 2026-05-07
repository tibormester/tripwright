from __future__ import annotations

import unittest

from backend.location.models import LocationContext
from backend.npc_agent.npc_profile import NPCProfile
from backend.research.models import ResearchReport
from backend.world_state import RuntimeSceneDefinition, WorldState


class RuntimeModelTests(unittest.TestCase):
    def test_runtime_models_round_trip(self) -> None:
        location = LocationContext(
            input_value="The Hoxton Williamsburg",
            input_kind="lodging_query",
            canonical_name="The Hoxton Williamsburg",
            formatted_address="97 Wythe Ave, Brooklyn, NY 11249, United States",
            latitude=40.7216,
            longitude=-73.9582,
            city="Brooklyn",
            neighborhood="Williamsburg",
            region="New York",
            country="United States",
            lodging_type="hotel",
            provider="nominatim",
            provider_place_id="way:12345",
            resolution_confidence=0.91,
            raw_metadata={"source": "test"},
        )
        research = ResearchReport(
            area_summary="Creative and walkable with plenty of low-key local stops.",
            tone_keywords=["creative", "walkable"],
            local_sayings=["take it easy"],
            demographic_archetypes=["locals", "visitors"],
            common_hobbies=["reading", "coffee"],
            social_norms=["keep it easygoing"],
            lodging_context="Use the hotel as the anchor.",
            destination_recommendation_notes=["Prefer short walks."],
            sources=[{"url": "https://example.com", "title": "Example"}],
            raw_snippets=[{"snippet": "Example snippet"}],
        )
        npc = NPCProfile.love_patel()
        scene = RuntimeSceneDefinition(
            location_id="lodging",
            category="lodging",
            label="The Hoxton Williamsburg",
            description="Arrive and get oriented.",
            location="the lobby of The Hoxton Williamsburg",
            narrator_text="After the blur of transit, you arrive.",
            place_metadata={"city": "Brooklyn"},
            scene_seed={"arrival_mood": "jetlagged"},
            npc_seed={"role": "Front Desk Host"},
            npc_profile=npc,
        )
        world = WorldState(
            world_id="lodg_test_world",
            created_at="2026-05-06T12:00:00+00:00",
            fingerprint="lodging_deadbeef",
            location_context=location,
            research_report=research,
            lodging_scene=scene,
            travel_scenes=[scene],
            generated_scene_cache={"lodging": scene},
            generated_npc_cache={"lodging": npc},
            metadata={"dynamic": True},
        )

        reloaded = WorldState.from_dict(world.to_dict())

        self.assertEqual(reloaded.world_id, world.world_id)
        self.assertEqual(reloaded.location_context.canonical_name, location.canonical_name)
        self.assertEqual(reloaded.research_report.tone_keywords, research.tone_keywords)
        self.assertEqual(reloaded.lodging_scene.location, scene.location)
        self.assertEqual(reloaded.generated_npc_cache["lodging"].name, npc.name)


if __name__ == "__main__":
    unittest.main()
