from __future__ import annotations

import unittest

from backend.npc_agent.assets import build_npc_asset_spec, build_rendering_context, build_scene_asset_spec
from backend.npc_agent.conversation_state import ConversationState
from backend.npc_agent.npc_profile import NPCProfile


class AssetRenderingTests(unittest.TestCase):
    def test_image_prompts_use_softer_more_stylized_art_direction(self) -> None:
        scene_spec = build_scene_asset_spec(location="a quiet cafe", narrator_text="Morning light softens the room.")
        npc_spec = build_npc_asset_spec(
            NPCProfile(
                name="Mina",
                background="test",
                role="Cafe Barista",
                speaking_style="test",
                physical_description="test",
                mental_description="test",
                emotional_description="test",
                local_flavor="test",
                beliefs="test",
            )
        )

        self.assertIn("stylized game-art illustration", scene_spec.prompt)
        self.assertIn("Avoid uncanny-valley realism", scene_spec.prompt)
        self.assertIn("stylized game-art character portrait", npc_spec.prompt)
        self.assertIn("Avoid uncanny-valley realism", npc_spec.prompt)

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
