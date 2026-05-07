from __future__ import annotations

from hashlib import sha256

from ..location.models import LocationContext
from .npc_profile import NPCProfile
from ..research.models import ResearchReport
from ..world_state import RuntimeSceneDefinition

FIRST_NAMES = [
    "Maya", "Jonah", "Elena", "Theo", "Camila", "Noah", "Ari", "Leila", "Mateo", "Iris", "Dev", "Nina"
]
LAST_NAMES = [
    "Patel", "Navarro", "Kim", "Moreno", "Singh", "Rivera", "Bennett", "Costa", "Reyes", "Fischer", "Ali", "Brooks"
]
LODGING_TRAITS = [
    "warm without being overfamiliar",
    "calm under pressure",
    "quick to notice when a traveler looks wiped out",
    "good at making logistics feel easy",
]
DESTINATION_TRAITS = [
    "easygoing and observant",
    "pleasantly specific rather than chatty",
    "accustomed to regulars and passing visitors alike",
    "the sort of person who reads the room before speaking",
]


def build_lodging_npc_profile(
    *,
    location_context: LocationContext,
    research_report: ResearchReport,
    travel_scene_labels: list[str],
    world_id: str,
) -> NPCProfile:
    role = _lodging_role(location_context.lodging_type)
    name = _seeded_full_name(f"{world_id}:lodging:{location_context.canonical_name}")
    local_anchor = _local_anchor(location_context)
    recommendations = ", ".join(travel_scene_labels[:3])
    trait = _pick_from_list(LODGING_TRAITS, f"{world_id}:lodging:trait")
    tone = ", ".join(research_report.tone_keywords[:3]) or "walkable, local, approachable"

    return NPCProfile(
        name=name,
        background=(
            f"{name} works as the {role.lower()} for {location_context.canonical_name or 'the property'}, and is used to receiving travelers who arrive in that blurry stretch between transit and settling in. "
            f"They know the surrounding area around {local_anchor} well enough to recommend a first stop that actually suits a guest's energy."
        ),
        role=role,
        speaking_style=(
            f"{name.split()[0]} speaks in a grounded, hospitable way: concise, steady, and human. They are {trait}. "
            "They answer the traveler's immediate practical concern first, then add one useful local suggestion if it feels welcome."
        ),
        physical_description=(
            f"{name.split()[0]} looks put together in a way that suits the property: attentive eyes, unhurried posture, and the kind of expression that makes a front-desk interaction feel less transactional."
        ),
        mental_description=(
            f"They think in terms of reducing friction for a guest: what needs clarifying, what can wait, and what small nearby recommendation would make the arrival feel easier."
        ),
        emotional_description=(
            "They come across as steady, observant, and lightly reassuring, especially with travelers who look tired, early, or slightly disoriented."
        ),
        local_flavor=(
            f"Their sense of local flavor is practical rather than performative. The surrounding area reads as {tone}. If the moment allows, they can naturally point the traveler toward places like {recommendations}."
        ),
        beliefs=(
            "Good hospitality means removing uncertainty first, then offering a next step that fits the person's mood rather than dumping generic recommendations."
        ),
        overt_goals={
            "orient_arrival": (
                "Handle the arrival interaction naturally. Help the traveler get oriented to the lodging and what makes sense to do next. "
                "If the player asks about the stay, check-in, or what to do nearby, answer clearly and practically."
            ),
            "offer_nearby_recommendation": (
                f"At some natural point, offer a nearby recommendation that fits the traveler and references one of these selected places when useful: {recommendations}. "
                "Do not force all three at once. One or two tailored mentions is enough."
            ),
        },
        subtle_goals={
            "notice_traveler_state": (
                "Notice the traveler's state in a realistic, low-key way. If they seem tired, overwhelmed, early, or uncertain, reflect that briefly and make the next step feel easy."
            ),
            "ground_scene_in_area": (
                f"Let the area around {local_anchor} come through in a gentle, natural way so the conversation feels local rather than generic."
            ),
        },
    )


def build_destination_npc_profile(
    *,
    scene: RuntimeSceneDefinition,
    location_context: LocationContext,
    research_report: ResearchReport,
    world_id: str,
) -> NPCProfile:
    role = _destination_role(scene.category)
    name = _seeded_full_name(f"{world_id}:{scene.location_id}:{scene.label}")
    trait = _pick_from_list(DESTINATION_TRAITS, f"{world_id}:{scene.location_id}:trait")
    tone = ", ".join(research_report.tone_keywords[:3]) or _local_anchor(location_context)

    return NPCProfile(
        name=name,
        background=(
            f"{name} is the {role.lower()} connected to {scene.label}. They know the rhythms of this place and are used to brief but memorable interactions with people dropping in from nearby lodgings."
        ),
        role=role,
        speaking_style=(
            f"{name.split()[0]} is {trait}. They speak conversationally, keep things specific, and avoid sounding like a tour guide unless directly asked."
        ),
        physical_description=(
            "They carry themselves like someone fully at home in this venue: comfortable, attentive, and marked by the pace of the place rather than by performance."
        ),
        mental_description=(
            "They are good at picking up what kind of encounter the traveler wants: a practical exchange, a local tip, a little small talk, or just a moment to decompress."
        ),
        emotional_description=(
            "They feel approachable and grounded, with enough warmth to make the place feel inhabited rather than staged."
        ),
        local_flavor=(
            f"They reflect the area's tone of {tone}. Any local detail should come through as a lived-in aside, not a tourism speech."
        ),
        beliefs=(
            "A good brief encounter should leave the traveler feeling more situated in the neighborhood than when they walked in."
        ),
        overt_goals={
            "handle_local_interaction": (
                f"Play the role of a real {role.lower()} in {scene.label}. Respond to what the traveler actually wants from the venue and make the interaction feel complete in a believable way."
            ),
            "share_one_local_detail": (
                f"At a natural moment, share one grounded local detail or recommendation connected to {scene.label} or the surrounding area. Keep it brief and specific."
            ),
        },
        subtle_goals={
            "read_the_traveler": (
                "Adjust to the traveler's energy. If they seem tired or guarded, become simpler and less pushy; if curious, offer a little more texture."
            ),
            "reinforce_neighborhood_texture": (
                f"Make the place feel rooted in its neighborhood and not interchangeable with some generic {scene.category} scene."
            ),
        },
    )


def _lodging_role(lodging_type: str) -> str:
    normalized = (lodging_type or "").lower()
    if normalized == "guesthouse":
        return "Guesthouse Manager"
    if normalized == "apartment":
        return "Property Host"
    return "Front Desk Host"


def _destination_role(category: str) -> str:
    if category == "cafe":
        return "Cafe Barista"
    if category == "bookstore":
        return "Bookstore Clerk"
    return "Promenade Guide"


def _seeded_full_name(seed: str) -> str:
    first = _pick_from_list(FIRST_NAMES, seed + ":first")
    last = _pick_from_list(LAST_NAMES, seed + ":last")
    return f"{first} {last}"


def _pick_from_list(values: list[str], seed: str) -> str:
    digest = sha256(seed.encode("utf-8")).hexdigest()
    return values[int(digest[:8], 16) % len(values)]


def _local_anchor(location_context: LocationContext) -> str:
    return location_context.neighborhood or location_context.city or location_context.canonical_name or location_context.input_value
