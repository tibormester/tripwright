# Dynamic Lodging World Implementation Checklist

## Phase 0 - Setup and dependency decisions
- [x] Confirm v1 input contract: `lodging_input` accepts Booking URL or fallback text
- [x] Decide whether dynamic mode should fully replace startup in the UI or exist beside static mode initially
- [x] Add/confirm Python dependencies:
  - [x] `requests`
  - [x] `beautifulsoup4`
  - [ ] optional `extruct`
  - [ ] optional DuckDuckGo search library
- [x] Create a `data/` directory convention for file-backed world persistence
- [x] Add config env vars for timeouts, store mode, and provider toggles

## Phase 1 - New runtime models
### Files
- [x] Create `backend/location/models.py`
- [x] Create `backend/research/models.py`
- [x] Create `backend/world_state.py`

### Tasks
- [x] Add `LocationContext` dataclass
- [x] Add `ResearchReport` dataclass
- [x] Add `RuntimeSceneDefinition` dataclass
- [x] Add `WorldState` dataclass
- [x] Add `to_dict()` / `from_dict()` helpers for all runtime models
- [x] Add optional cache maps for generated scenes/NPCs in `WorldState`

## Phase 2 - Persistence abstraction
### Files
- [x] Create `backend/world_store.py`

### Tasks
- [x] Define a store interface with methods like:
  - [x] `get_world(world_id)`
  - [x] `save_world(world_state)`
  - [x] `find_world_id_by_fingerprint(fingerprint)`
  - [x] `save_fingerprint_mapping(fingerprint, world_id)`
- [x] Implement `MemoryWorldStore`
- [x] Implement `FileWorldStore`
- [x] Add file layout:
  - [x] `data/world_index.json`
  - [x] `data/worlds/<world_id>/world.json`
- [x] Add canonical fingerprint builder for resolved lodging
- [x] Add world id generator

## Phase 3 - Lodging input resolution
### Files
- [x] Create `backend/location/booking_parser.py`
- [x] Create `backend/location/providers.py`
- [x] Create `backend/location/service.py`

### Tasks
- [x] Add URL detection helper
- [x] Add Booking.com hostname detection helper
- [x] Implement best-effort Booking page fetch using `requests`
- [x] Parse useful fields from Booking HTML:
  - [x] lodging name
  - [x] address
  - [x] coordinates if present
  - [x] city/neighborhood hints
  - [x] canonical URL
- [x] Add fallback resolution using Nominatim / OSM geocoding
- [x] Infer lodging type:
  - [x] hotel
  - [x] inn / guesthouse
  - [x] apartment / airbnb-like rental
  - [x] unknown lodging fallback
- [x] Build canonical `LocationContext`
- [x] Add confidence scoring / incomplete-data fallback behavior

## Phase 4 - Nearby destination lookup
### Files
- [x] Extend `backend/location/providers.py`
- [x] Create `backend/location/destination_selector.py`

### Tasks
- [x] Query Overpass/OSM around lodging coordinates
- [x] Collect candidates for:
  - [x] cafe / coffee shop
  - [x] bookstore / books / reading-oriented spots
  - [x] park / promenade / plaza / waterfront / square
- [x] Normalize candidate place objects
- [x] Rank candidates by distance + metadata quality
- [x] Apply category fallback rules
- [x] Select exactly 3 destinations
- [x] Produce stable `location_id` values

## Phase 5 - Research pipeline
### Files
- [x] Create `backend/research/prompts.py`
- [x] Create `backend/research/service.py`
- [x] Optional: create `backend/research/search_provider.py`

### Tasks
- [x] Implement fixed-query research pipeline
- [x] Generate area-level research queries from city/neighborhood
- [x] Fetch public search snippets if provider/library is available
- [x] Summarize into `ResearchReport`
- [x] Keep outputs soft and non-overclaiming
- [x] Store source snippets/URLs where possible
- [x] Add fallback behavior when search is unavailable

## Phase 6 - Runtime NPC and scene builders
### Files
- [x] Create `backend/npc_agent/runtime_profiles.py`
- [x] Create `backend/world_builder.py`

### Tasks
- [x] Build a lodging-staff role selector based on lodging type
- [x] Generate dynamic lodging NPC profile data
- [x] Generate dynamic lodging narrator intro text
- [x] Generate runtime lodging scene definition
- [x] Generate destination scene seeds
- [x] Generate destination NPC seeds for lazy creation
- [x] Preserve the current overt/subtle goal structure style
- [x] Ensure generated recommendations reference the selected 3 destinations

## Phase 7 - World-aware conversation integration
### Files to modify
- [x] `backend/app.py`
- [x] `backend/npc_agent/agent.py`
- [x] `backend/npc_agent/assets.py`
- [ ] `backend/npc_agent/scenes.py` or replace its static responsibility
- [x] `backend/npc_agent/conversation_state.py` if world linkage is needed

### Tasks
- [x] Add `POST /world/initialize`
- [x] Return `world_id`, `world`, and initialized `conversation`
- [x] Extend `POST /conversation/turn` to accept `world_id`
- [x] Load `WorldState` inside travel transitions
- [x] Replace static travel destination lookup with runtime world lookup
- [x] Lazy-generate destination scene and NPC when `/command N` is chosen
- [x] Cache generated destination scene/NPC back into the world store
- [x] Keep static `/conversation/initialize` available as fallback during migration

## Phase 8 - Rendering and assets
### Files to modify
- [x] `backend/npc_agent/assets.py`
- [ ] `backend/generate_assets.py` if needed

### Tasks
- [x] Make rendering context consume runtime travel scenes
- [x] Make scene labels and descriptions come from `WorldState`
- [x] Make NPC headshot generation support runtime-generated NPC profiles
- [x] Keep image generation optional for dynamic worlds in v1
- [x] Ensure asset keys are stable for cached runtime content

## Phase 9 - Frontend integration
### Files to modify
- [x] `public/app.js`
- [x] `public/index.html`
- [x] `public/styles.css`
- [ ] optional CLI updates in `cli/client.js`

### Tasks
- [x] Add startup form for lodging input
- [x] Support Booking URL paste flow
- [x] Add startup loading state
- [x] Store `world_id` client-side alongside conversation state
- [x] Send `world_id` with turn requests
- [x] Keep travel option rendering working with runtime options
- [x] Update restart behavior for dynamic worlds
- [ ] Optionally keep a “start static demo” button during migration

## Phase 10 - Error handling and fallback behavior
- [x] Add request timeouts for HTML fetch, geocoding, Overpass, and search
- [x] Add retry logic for transient failures
- [x] If Booking extraction fails, fallback to text-based location resolution
- [x] If geocoding fails, return a clear validation error to the client
- [x] If research fails, continue with generic-but-plausible local flavor
- [x] If nearby place lookup is weak, use broader category fallbacks
- [ ] If dynamic world generation fails entirely, optionally fallback to current static flow

## Phase 11 - Logging and observability
- [x] Log world creation start/end with `world_id`
- [x] Log lodging resolution source and confidence
- [x] Log selected destinations
- [x] Log research timings and failures
- [x] Log lazy destination generation events
- [x] Log cache hits for repeated lodging inputs

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
- [x] 1. Runtime models
- [x] 2. World store
- [x] 3. Lodging resolution
- [x] 4. Nearby destination lookup
- [x] 5. Research pipeline
- [x] 6. World builder
- [x] 7. New endpoint
- [x] 8. Turn/travel refactor
- [x] 9. Frontend startup flow
- [ ] 10. Hardening/tests

## Nice-to-have after v1
- [ ] planner-style search agent loop instead of fixed queries
- [ ] place-photo retrieval as reference material for scene generation
- [ ] external storage adapter for Vercel deployment
- [ ] world expiration / cache invalidation policy
- [ ] admin/debug endpoint to inspect stored worlds
