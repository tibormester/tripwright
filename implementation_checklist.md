# Dynamic Lodging World Implementation Checklist

## Phase 0 - Setup and dependency decisions
- [ ] Confirm v1 input contract: `lodging_input` accepts Booking URL or fallback text
- [ ] Decide whether dynamic mode should fully replace startup in the UI or exist beside static mode initially
- [ ] Add/confirm Python dependencies:
  - [ ] `requests`
  - [ ] `beautifulsoup4`
  - [ ] optional `extruct`
  - [ ] optional DuckDuckGo search library
- [ ] Create a `data/` directory convention for file-backed world persistence
- [ ] Add config env vars for timeouts, store mode, and provider toggles

## Phase 1 - New runtime models
### Files
- [ ] Create `backend/location/models.py`
- [ ] Create `backend/research/models.py`
- [ ] Create `backend/world_state.py`

### Tasks
- [ ] Add `LocationContext` dataclass
- [ ] Add `ResearchReport` dataclass
- [ ] Add `RuntimeSceneDefinition` dataclass
- [ ] Add `WorldState` dataclass
- [ ] Add `to_dict()` / `from_dict()` helpers for all runtime models
- [ ] Add optional cache maps for generated scenes/NPCs in `WorldState`

## Phase 2 - Persistence abstraction
### Files
- [ ] Create `backend/world_store.py`

### Tasks
- [ ] Define a store interface with methods like:
  - [ ] `get_world(world_id)`
  - [ ] `save_world(world_state)`
  - [ ] `find_world_id_by_fingerprint(fingerprint)`
  - [ ] `save_fingerprint_mapping(fingerprint, world_id)`
- [ ] Implement `MemoryWorldStore`
- [ ] Implement `FileWorldStore`
- [ ] Add file layout:
  - [ ] `data/world_index.json`
  - [ ] `data/worlds/<world_id>/world.json`
- [ ] Add canonical fingerprint builder for resolved lodging
- [ ] Add world id generator

## Phase 3 - Lodging input resolution
### Files
- [ ] Create `backend/location/booking_parser.py`
- [ ] Create `backend/location/providers.py`
- [ ] Create `backend/location/service.py`

### Tasks
- [ ] Add URL detection helper
- [ ] Add Booking.com hostname detection helper
- [ ] Implement best-effort Booking page fetch using `requests`
- [ ] Parse useful fields from Booking HTML:
  - [ ] lodging name
  - [ ] address
  - [ ] coordinates if present
  - [ ] city/neighborhood hints
  - [ ] canonical URL
- [ ] Add fallback resolution using Nominatim / OSM geocoding
- [ ] Infer lodging type:
  - [ ] hotel
  - [ ] inn / guesthouse
  - [ ] apartment / airbnb-like rental
  - [ ] unknown lodging fallback
- [ ] Build canonical `LocationContext`
- [ ] Add confidence scoring / incomplete-data fallback behavior

## Phase 4 - Nearby destination lookup
### Files
- [ ] Extend `backend/location/providers.py`
- [ ] Create `backend/location/destination_selector.py`

### Tasks
- [ ] Query Overpass/OSM around lodging coordinates
- [ ] Collect candidates for:
  - [ ] cafe / coffee shop
  - [ ] bookstore / books / reading-oriented spots
  - [ ] park / promenade / plaza / waterfront / square
- [ ] Normalize candidate place objects
- [ ] Rank candidates by distance + metadata quality
- [ ] Apply category fallback rules
- [ ] Select exactly 3 destinations
- [ ] Produce stable `location_id` values

## Phase 5 - Research pipeline
### Files
- [ ] Create `backend/research/prompts.py`
- [ ] Create `backend/research/service.py`
- [ ] Optional: create `backend/research/search_provider.py`

### Tasks
- [ ] Implement fixed-query research pipeline
- [ ] Generate area-level research queries from city/neighborhood
- [ ] Fetch public search snippets if provider/library is available
- [ ] Summarize into `ResearchReport`
- [ ] Keep outputs soft and non-overclaiming
- [ ] Store source snippets/URLs where possible
- [ ] Add fallback behavior when search is unavailable

## Phase 6 - Runtime NPC and scene builders
### Files
- [ ] Create `backend/npc_agent/runtime_profiles.py`
- [ ] Create `backend/world_builder.py`

### Tasks
- [ ] Build a lodging-staff role selector based on lodging type
- [ ] Generate dynamic lodging NPC profile data
- [ ] Generate dynamic lodging narrator intro text
- [ ] Generate runtime lodging scene definition
- [ ] Generate destination scene seeds
- [ ] Generate destination NPC seeds for lazy creation
- [ ] Preserve the current overt/subtle goal structure style
- [ ] Ensure generated recommendations reference the selected 3 destinations

## Phase 7 - World-aware conversation integration
### Files to modify
- [ ] `backend/app.py`
- [ ] `backend/npc_agent/agent.py`
- [ ] `backend/npc_agent/assets.py`
- [ ] `backend/npc_agent/scenes.py` or replace its static responsibility
- [ ] `backend/npc_agent/conversation_state.py` if world linkage is needed

### Tasks
- [ ] Add `POST /world/initialize`
- [ ] Return `world_id`, `world`, and initialized `conversation`
- [ ] Extend `POST /conversation/turn` to accept `world_id`
- [ ] Load `WorldState` inside travel transitions
- [ ] Replace static travel destination lookup with runtime world lookup
- [ ] Lazy-generate destination scene and NPC when `/command N` is chosen
- [ ] Cache generated destination scene/NPC back into the world store
- [ ] Keep static `/conversation/initialize` available as fallback during migration

## Phase 8 - Rendering and assets
### Files to modify
- [ ] `backend/npc_agent/assets.py`
- [ ] `backend/generate_assets.py` if needed

### Tasks
- [ ] Make rendering context consume runtime travel scenes
- [ ] Make scene labels and descriptions come from `WorldState`
- [ ] Make NPC headshot generation support runtime-generated NPC profiles
- [ ] Keep image generation optional for dynamic worlds in v1
- [ ] Ensure asset keys are stable for cached runtime content

## Phase 9 - Frontend integration
### Files to modify
- [ ] `public/app.js`
- [ ] `public/index.html`
- [ ] `public/styles.css`
- [ ] optional CLI updates in `cli/client.js`

### Tasks
- [ ] Add startup form for lodging input
- [ ] Support Booking URL paste flow
- [ ] Add startup loading state
- [ ] Store `world_id` client-side alongside conversation state
- [ ] Send `world_id` with turn requests
- [ ] Keep travel option rendering working with runtime options
- [ ] Update restart behavior for dynamic worlds
- [ ] Optionally keep a “start static demo” button during migration

## Phase 10 - Error handling and fallback behavior
- [ ] Add request timeouts for HTML fetch, geocoding, Overpass, and search
- [ ] Add retry logic for transient failures
- [ ] If Booking extraction fails, fallback to text-based location resolution
- [ ] If geocoding fails, return a clear validation error to the client
- [ ] If research fails, continue with generic-but-plausible local flavor
- [ ] If nearby place lookup is weak, use broader category fallbacks
- [ ] If dynamic world generation fails entirely, optionally fallback to current static flow

## Phase 11 - Logging and observability
- [ ] Log world creation start/end with `world_id`
- [ ] Log lodging resolution source and confidence
- [ ] Log selected destinations
- [ ] Log research timings and failures
- [ ] Log lazy destination generation events
- [ ] Log cache hits for repeated lodging inputs

## Phase 12 - Testing
### Unit tests
- [ ] fingerprint generation is stable
- [ ] runtime models serialize/deserialize cleanly
- [ ] Booking parser handles representative HTML inputs
- [ ] fallback geocoding path works
- [ ] destination selector returns exactly 3 destinations
- [ ] world builder creates lodging scene + seeds

### Integration tests
- [ ] `/world/initialize` with fallback text input
- [ ] `/world/initialize` with Booking URL input
- [ ] repeated same lodging returns same `world_id`
- [ ] `/conversation/turn` works with `world_id`
- [ ] travel command lazily generates destination scene/NPC
- [ ] revisit destination uses cached generated content

## Suggested implementation order
- [ ] 1. Runtime models
- [ ] 2. World store
- [ ] 3. Lodging resolution
- [ ] 4. Nearby destination lookup
- [ ] 5. Research pipeline
- [ ] 6. World builder
- [ ] 7. New endpoint
- [ ] 8. Turn/travel refactor
- [ ] 9. Frontend startup flow
- [ ] 10. Hardening/tests

## Nice-to-have after v1
- [ ] planner-style search agent loop instead of fixed queries
- [ ] place-photo retrieval as reference material for scene generation
- [ ] external storage adapter for Vercel deployment
- [ ] world expiration / cache invalidation policy
- [ ] admin/debug endpoint to inspect stored worlds
