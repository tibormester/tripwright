# Dynamic Lodging-Driven NPC Generation Plan

## Confirmed Product Decisions

These decisions are now locked in based on the latest requirements.

### Startup input
The preferred startup input is a **Booking.com listing URL**.

However, because the Booking.com API is gated and we do not have API access, the backend should support this input model:

1. **Primary input:** Booking.com listing URL
2. **Fallback input:** freeform lodging query or address
   - hotel name
   - Airbnb / guesthouse / inn name
   - address
   - hotel + city

### Starting place type
The starting place is always a **lodging**.

The first NPC should therefore always be a lodging staff equivalent, adapted to the lodging type:
- hotel -> receptionist / front desk staff
- inn / guesthouse -> owner / manager
- Airbnb / short-term rental -> host / property manager

### Startup latency
A multi-second startup flow is acceptable.

This means world generation can be done synchronously in a blocking request for v1, as long as the frontend can show a loading state.

### Provider/API constraints
There is no non-public API access available.

So v1 should rely on:
- public web page fetching where feasible
- public geocoding/place data
- public or unofficial web search libraries if needed
- no gated Booking API
- no Google Places requirement

### Destination count
Exactly **3 travel destinations** should be generated each time.

Recommended categories:
- coffee shop / cafe
- bookstore / reading-oriented spot
- park / promenade / green / waterfront space

### Images
Place image retrieval is **v2**.

If used later, place photos would be only **reference material for generated art**, not shown raw.

### Persistence
Generated content should be associated with an ID and reused when the same link/address is submitted again.

Desired behavior:
- same lodging input -> same resolved canonical location -> same saved world id if already built
- generated JSON and PNG artifacts can be cached server-side

---

## Important Deployment Note: Vercel and Persistence

### Local disk persistence is fine for local dev or a long-running server
If this app is run on:
- a local machine
- a VPS
- a normal long-lived backend process

then saving world JSON and PNG files to a server folder is straightforward and reasonable.

### Vercel serverless is **not** a good fit for local-file persistence
If this backend runs on Vercel serverless functions:
- memory is not shared reliably across invocations
- local filesystem writes are ephemeral / not durable
- you cannot rely on one request seeing files written by another request long-term

So for Vercel:
- **in-memory state alone is not enough**
- **filesystem persistence alone is not enough**
- you would need external persistence such as:
  - Vercel Blob / S3-style storage for PNG/JSON files
  - a DB or key-value store for id lookup and metadata

### Recommendation
For implementation, structure persistence behind an interface:
- `MemoryWorldStore` for local testing
- `FileWorldStore` for local persistent dev/server deployments
- later `ExternalWorldStore` for Vercel-compatible deployment

So yes: **file + id persistence is fine architecturally**, but **not if you depend on Vercel local disk as the permanent store**.

---

## Current Backend Snapshot

The current Python backend is fully static:

- `backend/app.py`
  - `POST /conversation/initialize` starts a hardcoded hotel scene immediately
- `backend/npc_agent/scenes.py`
  - hardcodes hotel + 3 follow-up destinations
- `backend/npc_agent/npc_profile.py`
  - loads fixed NPC prompt modules such as `love_patel.py`
- `backend/npc_agent/agent.py`
  - assumes the next locations already exist
- `backend/npc_agent/assets.py`
  - generates image prompts from static scene/NPC data

The current code does **not** have:
- a world/session layer
- dynamic location normalization
- lodging link parsing
- research orchestration
- lazy destination NPC generation
- persistent world caching

---

## Product Goal

Replace the fixed startup flow with a dynamic lodging-aware world generation flow:

1. user submits a Booking.com URL or fallback lodging query
2. backend resolves the lodging into canonical place data
3. backend researches the surrounding area
4. backend generates a dynamic lodging intro scene
5. backend generates a lodging staff NPC
6. backend creates exactly 3 nearby destinations
7. destination NPCs are generated lazily only when visited
8. world data is cached by a stable id

---

## Functional Requirements

## 1. New startup endpoint
Add a new endpoint on top of the existing system.

Recommended endpoint:

### `POST /world/initialize`
Request:
```json
{
  "lodging_input": "https://www.booking.com/hotel/...html"
}
```

Fallback request:
```json
{
  "lodging_input": "The Hoxton Williamsburg"
}
```

Response should include:
- `world_id`
- resolved lodging metadata
- dynamic world/session data
- initialized first conversation

The existing `POST /conversation/initialize` can remain as static/dev fallback during migration.

---

## 2. Lodging input resolution
The system should accept either:
- Booking.com listing URL
- freeform lodging text/address

### Booking URL handling
Because we do not have Booking API access, v1 should use a **best-effort extractor**:
- fetch the HTML page with `requests`
- parse useful metadata from:
  - JSON-LD if present
  - OpenGraph tags
  - page title / canonical link
  - embedded structured fields if accessible
- extract at least:
  - lodging name
  - address if available
  - coordinates if available
  - city / neighborhood hints if available

This may be brittle, so it must have fallback behavior.

### Fallback resolution strategy
If Booking extraction fails or is incomplete:
- use the extracted hotel name + city hints as a query
- or use the raw user-provided lodging string
- resolve it through public geocoding/place lookup

### Recommended public provider stack for v1
To avoid gated APIs, use:
- **Nominatim / OpenStreetMap** for geocoding/place normalization
- **Overpass API / OSM** for nearby destination lookup
- optional **DuckDuckGo search library** for local culture research

This is the simplest realistic public stack.

---

## 3. Research flow
The backend should perform a research stage before starting the game.

Research targets:
- city/neighborhood vibe
- likely local sayings/slang
- social texture / archetypes
- common hobbies/interests
- traveler-relevant local flavor
- plausible nearby attractions
- lodging context

### Important simplification for v1
Do **not** scrape Booking.com's “nearby attractions” UI in v1.

Reason:
- brittle
- likely bot-fragile
- not needed if OSM nearby place lookup works

Instead:
- use OSM/Overpass for nearby place candidates
- use web search only for broader cultural flavor

---

## 4. Research agent design
The research stage should feel agent-like, but v1 should stay simple.

### Recommended v1 approach
Use a **fixed query research pipeline**, not a fully autonomous search agent.

Example fixed queries:
- `vibe of <neighborhood/city>`
- `local slang or sayings in <city/neighborhood>`
- `popular hobbies or hangouts in <city/neighborhood>`
- `what is <neighborhood/city> known for`

Then:
- fetch a small number of snippets/results
- summarize into a structured `ResearchReport`

### Optional v1.5 / v2 upgrade
If wanted later, replace the fixed pipeline with a planner loop:
- model emits `search` or `finish`
- backend executes search requests
- model keeps iterating until goal is complete

That matches the earlier agent/tool-call concept, but it should come after the simpler pipeline works.

---

## 5. Dynamic world generation
Research output should feed a runtime world builder.

The generated world should include:
- lodging scene
- exactly 3 destination options
- shared area flavor
- selected nearby places
- generated lodging-staff NPC profile
- lazy generation seeds for the destination NPCs

---

## 6. Dynamic first NPC
Replace Love Patel with a generated lodging staff character.

The role should adapt to lodging type:
- hotel -> receptionist
- guesthouse / inn -> owner or manager
- Airbnb -> host / property manager

The conversation function remains similar to the existing hotel flow:
- orient the traveler
- respond to arrival context
- offer useful nearby recommendations
- reflect researched local flavor naturally

---

## 7. Dynamic lodging scene
The first location should be generated from the resolved lodging.

It should include:
- dynamic location string
- narrator intro text
- lodging description informed by available metadata
- NPC role framing appropriate to lodging type

---

## 8. Exactly 3 dynamic travel destinations
Always produce exactly 3 destination options.

Preferred category assignment:
1. cafe / coffee shop
2. bookstore / reading-oriented spot
3. park / promenade / square / green space

Fallback rules:
- if no bookstore is found, use a library-adjacent or quiet reading-style venue
- if no park is found, use promenade / plaza / waterfront / square
- if no cafe is found, use bakery / tea shop / brunch spot

Each destination should include:
- `location_id`
- label
- short description
- place metadata
- scene seed
- NPC generation seed

---

## 9. Lazy destination NPC generation
Do not generate all destination NPCs up front.

Instead:
- generate only the lodging NPC during world initialization
- when the player travels to a destination, generate:
  - that destination's scene text
  - that destination's NPC profile
- cache the result under the world id

This is the main structural change requested to reduce startup work.

---

## 10. Persistence and world ids
Generated worlds should be stored and reused.

### Required behavior
- normalize the resolved lodging into a canonical fingerprint
- map that fingerprint to a stable `world_id`
- save generated world data under that id
- if the same lodging is requested again, return the existing world

### Suggested storage model
#### Index
A small index mapping:
- canonical lodging fingerprint -> `world_id`

#### World files
Per world id:
- `world.json`
- generated scene/NPC metadata
- optionally generated image metadata and PNG files later

### Recommendation for v1
Implement storage behind an abstraction and ship with:
- memory store
- file store

Then keep Vercel/external persistence as a deployment follow-up.

---

## 11. Preserve current conversation engine
The best implementation path is still to add a layer on top.

Keep using:
- `ConversationState`
- prompt builder
- model JSON response parsing
- flag completion logic
- rendering payload shape

What changes:
- scene definitions become runtime data
- NPC profiles become runtime-generated data
- travel options come from `WorldState`
- `/command N` should consult runtime world state instead of static tuples

---

## Recommended Technical Approach

## A. New runtime data layer
Add a dynamic world/session layer above the existing NPC engine.

### Core new models
#### `LocationContext`
Canonical lodging/place metadata.

Suggested fields:
- `input_value`
- `input_kind` (`booking_url`, `lodging_query`, `address`)
- `source_url`
- `canonical_name`
- `formatted_address`
- `latitude`
- `longitude`
- `city`
- `neighborhood`
- `region`
- `country`
- `lodging_type`
- `provider`
- `provider_place_id`
- `resolution_confidence`

#### `ResearchReport`
Structured area research summary.

Suggested fields:
- `area_summary`
- `tone_keywords`
- `local_sayings`
- `demographic_archetypes`
- `common_hobbies`
- `social_norms`
- `lodging_context`
- `destination_recommendation_notes`
- `sources`

#### `RuntimeSceneDefinition`
Dynamic equivalent of the current static `SceneDefinition`.

Suggested fields:
- `location_id`
- `category`
- `label`
- `description`
- `location`
- `narrator_text`
- `place_metadata`
- `scene_seed`
- `npc_seed`
- `npc_profile` optional

#### `WorldState`
Persistent session/world container.

Suggested fields:
- `world_id`
- `created_at`
- `location_context`
- `research_report`
- `lodging_scene`
- `travel_scenes`
- `generated_scene_cache`
- `generated_npc_cache`

---

## B. Public provider strategy

### 1. Lodging resolution
Primary options:
- Booking page HTML extraction
- Nominatim normalization fallback

Useful libraries:
- `requests`
- `beautifulsoup4`
- optional `extruct` for JSON-LD extraction

### 2. Nearby destinations
Use Overpass / OpenStreetMap around the resolved coordinates.

Search categories:
- cafe
- bookstore / books
- park / promenade / square / waterfront

### 3. Culture/local-flavor research
Use a public search library if needed, such as DuckDuckGo-based search.

This is lower confidence than formal APIs, so the prompting and summarization should stay soft and non-overclaiming.

---

## C. API design

### `POST /world/initialize`
Creates or loads a world, then returns the initialized first conversation.

Request:
```json
{
  "lodging_input": "https://www.booking.com/hotel/...html"
}
```

Response:
```json
{
  "world_id": "lodg_...",
  "world": { ... },
  "conversation": { ... }
}
```

### `POST /conversation/turn`
Continue using the existing endpoint, but make it world-aware.

Recommended addition:
```json
{
  "world_id": "lodg_...",
  "state": { ... },
  "user_input": "hello"
}
```

Then when a travel command is selected:
- load the world by id
- lazily generate the chosen destination if needed
- start that new scene

### Optional retrieval endpoint
#### `GET /world/<world_id>`
Useful for debugging or reloading a known world.

---

## D. Storage strategy

### Development-friendly v1
Implement:
- `MemoryWorldStore`
- `FileWorldStore`

File layout example:
- `data/world_index.json`
- `data/worlds/<world_id>/world.json`
- `data/worlds/<world_id>/assets/...`

### Stable fingerprinting
Fingerprint candidate fields:
- normalized lodging name
- normalized formatted address
- lat/lng rounded to stable precision

Use that fingerprint to look up an existing world id.

---

## Implementation Phases

## Phase 0 - finalize v1 decisions
Tasks:
- lock Booking URL + fallback text input contract
- lock public provider stack
- lock file-store vs memory-store dev mode
- keep images out of v1

## Phase 1 - runtime world models and storage
Tasks:
- add `LocationContext`, `ResearchReport`, `RuntimeSceneDefinition`, `WorldState`
- add store abstraction
- add memory store
- add file store
- add fingerprint index lookup

## Phase 2 - lodging input resolution
Tasks:
- add Booking page fetch + metadata extraction
- add fallback text/address resolution via Nominatim
- infer lodging type
- normalize to canonical `LocationContext`

## Phase 3 - nearby destination lookup
Tasks:
- query Overpass/OSM around the lodging coordinates
- select exactly 3 destination candidates
- apply category fallback rules

## Phase 4 - area research pipeline
Tasks:
- implement fixed search query pipeline
- summarize results into `ResearchReport`
- keep claims soft and grounded

## Phase 5 - runtime world builder
Tasks:
- generate lodging scene
- generate lodging staff NPC profile
- generate destination seeds
- save or load world by stable id

## Phase 6 - world-aware conversation flow
Tasks:
- add `POST /world/initialize`
- extend turn flow with `world_id`
- refactor travel handling to use `WorldState`
- lazy-generate destination scene/NPC on travel

## Phase 7 - frontend integration
Tasks:
- add startup form for Booking URL / lodging input
- show loading state during world generation
- store `world_id` client-side with conversation state
- preserve restart and travel behavior

## Phase 8 - hardening
Tasks:
- add timeouts/retries
- add low-confidence fallbacks
- add logging for resolution, research, generation, caching
- add graceful fallback to static mode when dynamic setup fails

---

## Recommended First Implementation Cut

The best first version is:

1. new `POST /world/initialize`
2. input accepts Booking URL or fallback lodging text
3. Booking URL parsed best-effort from page HTML
4. fallback normalization through Nominatim
5. nearby destinations from Overpass/OSM
6. fixed-query local flavor research
7. dynamic lodging scene + dynamic receptionist/host
8. exactly 3 destinations
9. lazy destination NPC generation
10. memory + file store abstraction for reuse

---

## Acceptance Criteria

A first successful version should satisfy all of these:

- user can paste a Booking.com URL or lodging query
- backend resolves the lodging into canonical metadata
- backend generates a world id and caches world data
- backend creates a dynamic lodging scene
- Love Patel is replaced by a generated lodging staff NPC in dynamic mode
- exactly 3 nearby destinations are available
- those destinations are based on actual nearby place candidates, not hardcoded ones
- destination NPCs are only generated when visited
- repeated requests for the same lodging can reuse the existing world id
- existing conversation flow continues to work on top of the new world layer

---

## Recommendation Summary

The architecture should still be:
- **add a new layer on top**, not rewrite the NPC engine

For v1, use:
- **Booking URL as preferred input**
- **fallback lodging text input**
- **best-effort HTML extraction for Booking pages**
- **Nominatim + Overpass** for public place resolution and nearby destinations
- **fixed-query research pipeline** for local flavor
- **exactly 3 destinations**
- **lazy destination NPC generation**
- **memory/file persistence abstraction**
- **no place image retrieval yet**

This keeps the implementation realistic with only public resources while matching the desired player experience.
