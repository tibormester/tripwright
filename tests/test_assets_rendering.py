from __future__ import annotations

import unittest

from backend.npc_agent.assets import build_rendering_context
from backend.npc_agent.conversation_state import ConversationState
from backend.npc_agent.npc_profile import NPCProfile


class AssetRenderingTests(unittest.TestCase):
    def test_runtime_rendering_uses_static_fallback_assets_when_dynamic_assets_are_missing(self) -> None:
        state = ConversationState(
            location="the counter and seating area at Totally New Cafe",
            npc_profile=NPCProfile(
                name="Brand New Barista",
                background="test",
                role="Cafe Barista",
                speaking_style="test",
                physical_description="test",
                mental_description="test",
                emotional_description="test",
                local_flavor="test",
                beliefs="test",
            ),
            scene_label="Totally New Cafe",
            scene_description="A dynamic scene without pre-generated images.",
            location_id="cafe_test",
            system_context={"scene_category": "cafe", "narrator_text": "You arrive at a cafe."},
        )

        rendering = build_rendering_context(state)

        self.assertTrue(rendering["scene"]["background"]["url"])
        self.assertTrue(rendering["scene"]["background"]["using_fallback"])
        self.assertTrue(rendering["npc"]["headshot"]["url"])
        self.assertTrue(rendering["npc"]["headshot"]["using_fallback"])


if __name__ == "__main__":
    unittest.main()
