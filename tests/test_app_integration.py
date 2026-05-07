from __future__ import annotations

import unittest
from unittest.mock import patch

import backend.app as backend_app
from backend.location.providers import OverpassPlace
from backend.npc_agent.conversation_state import DialogueTurn
from backend.research.models import ResearchReport


class FakeLodgingResolutionService:
    def resolve(self, lodging_input: str):
        from backend.location.models import LocationContext
        from backend.location.service import ResolutionResult

        input_kind = "booking_url" if lodging_input.startswith("https://www.booking.com/") else "lodging_query"
        return ResolutionResult(
            location_context=LocationContext(
                input_value=lodging_input,
                input_kind=input_kind,
                canonical_name="The Hoxton Williamsburg",
                formatted_address="97 Wythe Ave, Brooklyn, New York, United States",
                latitude=40.7216,
                longitude=-73.9582,
                city="Brooklyn",
                neighborhood="Williamsburg",
                region="New York",
                country="United States",
                lodging_type="hotel",
                provider="nominatim",
                provider_place_id="way:12345",
                resolution_confidence=0.9,
            )
        )


class FakeResearchService:
    def __init__(self) -> None:
        self.calls = 0

    def research_area(self, location_context):
        self.calls += 1
        return ResearchReport(
            area_summary="Creative waterfront blocks with easy low-key stops.",
            tone_keywords=["creative", "walkable", "waterfront"],
            destination_recommendation_notes=["Short, low-pressure neighborhood stops work well here."],
            social_norms=["keep it easygoing"],
            common_hobbies=["coffee", "reading", "walking"],
        )


class FakeOverpassProvider:
    def search_nearby(self, **kwargs):
        tag_filters = kwargs["tag_filters"]
        if ("amenity", "cafe") in tag_filters or ("shop", "bakery") in tag_filters:
            return [OverpassPlace("node", "1", "Daybreak Cafe", 40.0, -73.0, {"name": "Daybreak Cafe", "amenity": "cafe"}, "12 Main St", 120.0, {})]
        if ("shop", "books") in tag_filters:
            return []
        return [OverpassPlace("node", "3", "Riverfront Square", 40.0, -73.0, {"name": "Riverfront Square", "place": "square"}, "River Rd", 450.0, {})]


class FailingLodgingResolutionService:
    def resolve(self, lodging_input: str):
        raise ValueError("Unable to resolve lodging input into a canonical location")


class AppIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = backend_app.app.test_client()
        self.fake_research = FakeResearchService()
        object.__setattr__(backend_app.config, "enable_inline_image_data", True)
        backend_app.lodging_resolution_service = FakeLodgingResolutionService()
        backend_app.research_service = self.fake_research
        backend_app.destination_selector.overpass_provider = FakeOverpassProvider()
        backend_app.world_store = backend_app.create_world_store(backend_app.config)

        self.call_model_patch = patch(
            "backend.npc_agent.agent.call_model",
            side_effect=self._fake_call_model,
        )
        self.call_model_patch.start()
        self.addCleanup(self.call_model_patch.stop)

        self.inline_image_patcher = patch(
            "backend.app.generate_inline_asset_data_urls",
            side_effect=lambda specs, model, size, quality, output_format, best_effort=False: {
                f"{spec.kind}:{spec.key}": "data:image/jpeg;base64,dGVzdA==" for spec in specs
            },
        )
        self.inline_image_patch = self.inline_image_patcher.start()
        self.addCleanup(self.inline_image_patcher.stop)

    def _fake_call_model(self, prompt: str) -> DialogueTurn:
        dialogue = "Welcome — I can help you get oriented and point you somewhere nearby."
        if "Bookstore Clerk" in prompt:
            dialogue = "Welcome to the reading room. Let me know if you want a recommendation or a quiet corner."
        elif "Cafe Barista" in prompt:
            dialogue = "Welcome in. I can get you something easy and quick if you just arrived."
        elif "Promenade Guide" in prompt:
            dialogue = "It is a good stretch for a breather if you want to ease into the neighborhood."
        return DialogueTurn(speaker="NPC", dialogue=dialogue, thinking="test", flags=[])

    def test_world_initialize_with_text_input(self) -> None:
        response = self.client.post("/world/initialize", json={"lodging_input": "The Hoxton Williamsburg"})
        payload = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["world"]["location_context"]["canonical_name"], "The Hoxton Williamsburg")
        self.assertEqual(len(payload["world"]["travel_scenes"]), 3)
        self.assertEqual(payload["conversation"]["world_id"], payload["world_id"])
        self.assertIn("research_report", payload["conversation"]["system_context"])
        self.assertTrue(payload["conversation"]["rendering"]["scene"]["background"]["url"].startswith("data:image/jpeg;base64,"))

    def test_world_initialize_with_booking_url_and_cache_reuse(self) -> None:
        booking_url = "https://www.booking.com/hotel/us/the-hoxton-williamsburg.html"
        first = self.client.post("/world/initialize", json={"lodging_input": booking_url}).get_json()
        second = self.client.post("/world/initialize", json={"lodging_input": booking_url}).get_json()

        self.assertEqual(first["world_id"], second["world_id"])
        self.assertEqual(self.fake_research.calls, 1)

    def test_conversation_turn_and_lazy_travel_generation(self) -> None:
        initialized = self.client.post("/world/initialize", json={"lodging_input": "The Hoxton Williamsburg"}).get_json()
        state = initialized["conversation"]
        state["location"] = state["location"] + " [travel-selection]"

        response = self.client.post(
            "/conversation/turn",
            json={
                "state": state,
                "world_id": initialized["world_id"],
                "user_input": "/command 1",
            },
        )
        payload = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["scene_label"], "Daybreak Cafe")
        self.assertEqual(payload["world_id"], initialized["world_id"])
        self.assertIn("research_report", payload["system_context"])

    def test_travel_options_endpoint_streams_one_option_at_a_time(self) -> None:
        initialized = self.client.post("/world/initialize", json={"lodging_input": "The Hoxton Williamsburg"}).get_json()
        self.inline_image_patch.reset_mock()

        state = backend_app.ConversationState.from_dict(initialized["conversation"])
        state.location = state.location + " [travel-selection]"
        serialized = backend_app._serialize_state_payload(state)

        self.assertTrue(serialized["rendering"]["travel_selection"])
        self.assertEqual(serialized["rendering"]["travel_options"], [])
        self.assertTrue(serialized["rendering"]["travel_options_loading"])
        self.inline_image_patch.assert_not_called()

        chunk = self.client.post(
            "/world/travel-options/next",
            json={"world_id": initialized["world_id"], "loaded_option_ids": []},
        ).get_json()
        self.assertIsNotNone(chunk["option"])
        self.assertEqual(chunk["progress"]["loaded"], 1)

    def test_long_conversation_gets_narrator_wrap_up_hint(self) -> None:
        initialized = self.client.post("/world/initialize", json={"lodging_input": "The Hoxton Williamsburg"}).get_json()
        state = initialized["conversation"]

        for index in range(6):
            response = self.client.post(
                "/conversation/turn",
                json={
                    "state": state,
                    "world_id": initialized["world_id"],
                    "user_input": f"turn {index + 1}",
                },
            )
            self.assertEqual(response.status_code, 200)
            state = response.get_json()

        narrator_turns = [
            turn for turn in state["conversation_history"] if turn.get("speaker") == "Narrator"
        ]
        self.assertTrue(narrator_turns)
        self.assertIn("might be time to wrap up the conversation and say bye", narrator_turns[-1]["dialogue"])

    def test_unknown_world_id_returns_404(self) -> None:
        initialized = self.client.post("/world/initialize", json={"lodging_input": "The Hoxton Williamsburg"}).get_json()
        response = self.client.post(
            "/conversation/turn",
            json={
                "state": initialized["conversation"],
                "world_id": "missing_world",
                "user_input": "hello",
            },
        )

        self.assertEqual(response.status_code, 404)

    def test_world_initialize_falls_back_to_static_fallback_data(self) -> None:
        backend_app.lodging_resolution_service = FailingLodgingResolutionService()

        response = self.client.post("/world/initialize", json={"lodging_input": "not a real place"})
        payload = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["fallback_mode"])
        self.assertIsNone(payload["world_id"])
        self.assertIn("Fallback", payload["conversation"]["scene_label"])
        self.assertTrue(payload["conversation"]["system_context"]["fallback_mode"])


if __name__ == "__main__":
    unittest.main()
