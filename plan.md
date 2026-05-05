# NPC Conversation Agent Plan

## Goal
Build a simple Python prototype for a human-like NPC conversation agent using the OpenAI API.

This first version should focus on clean internal logic, modular prompt construction, and JSON-serializable state so it can later be sent over HTTP or integrated into a larger backend.

## Scope for v1
- No separate narrator agent
- No live web search yet
- No formal tool-calling API machinery
- No conversation summarization or advanced context compression
- No UI / CLI / input-output layer yet
- No config file yet

The goal is to build the core agent logic only.

---

## High-Level Decisions

### 1. Narration
Narration will be static, prewritten text rather than a separate LLM pass.

This keeps the prototype simpler and avoids unnecessary API calls.

Examples of static narration:
- setting intro
- NPC visual intro
- first-contact setup
- scene transition / farewell beat

### 2. Conversation State
Conversation state should be implemented as a JSON-serializable dictionary or class.

Reason:
- easy to inspect while prototyping
- easy to serialize and send over HTTP later
- easy to persist or restore

The state object should hold only conversation state, not prompt-building logic.

### 3. Structured LLM Output
Use JSON mode for the NPC response.

Keep the schema minimal.

Proposed response structure:
- `dialogue`: what the NPC says to the user
- `thoughts`: internal NPC reasoning / hidden commentary
- `flags`: list of string flags raised during the turn

Example:
```json
{
  "dialogue": "Welcome in. You look like you've had a long journey.",
  "thoughts": "The guest seems tired. I should keep things warm and efficient while learning what kind of place they'd enjoy nearby.",
  "flags": "<checked_in></checked_in>, <coffee_culture></coffee_culture>"
}
```

Flags act like lightweight tool calls.

## Architecture

The implementation should follow single-responsibility principles.

## Turn Flow

### Conversation Setup
1. Create static narration text
2. Create or load NPC profile
3. Create conversation state
4. Build the agent through the agent builder
5. Seed the state with the static scene context


### NPC Turn
1. Receive user input
2. Append user input to dialogue history
3. Build prompt from:
   - base instructions
   - realism constraints
   - NPC profile
   - current conversation state
   - dialogue history
   - JSON output instructions
4. Call OpenAI API
5. Parse JSON output
6. Validate / normalize fields:
   - `dialogue`
   - `thoughts`
   - `flags`
7. Append NPC dialogue to history
8. Update state using any flags
9. Return result

## Prompt Design

The prompt should be modular.

### Prompt Sections

#### Prefix / System Instructions
Contains:
- role and identity of the NPC
- behavioral rules
- realism constraints
- output format rules

#### Injected NPC Content
Contains:
- personality
- overt goals
- subtle goals
- local flavor
- speaking style

#### Runtime Context
Contains:
- scene setup
- conversation history
- current completed goals / active flags

#### Suffix / Output Contract
Contains:
- instruction to respond with JSON only
- required keys: `dialogue`, `thoughts`, `flags`
- rules for flags when goals are met

---

## Goal Handling

Goals should remain simple for v1.

### Overt Goals
These are explicit job/task goals.
Example:
- greet the guest
- determine their need
- explain room status
- offer alternatives

### Subtle Goals
These are flavor/social goals.
Example:
- surface local knowledge naturally
- learn a user preference
- guide toward a fitting recommendation

---

## Deferred Work

These should be explicitly postponed until after the first working prototype:

- web search for location-aware NPC enrichment
- automated generation of NPC profile text from location research
- advanced memory management / summarization
- formal tool calling
- HTTP transport layer
- frontend / CLI interaction loop
- multiple NPC support if it complicates v1

---

## Implementation Priorities


### Phase 3
- add one concrete example NPC
- test multi-turn conversation behavior
- refine prompt realism constraints

### Phase 4
- prepare for later HTTP integration
- optionally add profile enrichment pipeline

---

## Notes for Coding

- prioritize readability over abstraction
- keep class responsibilities narrow
- avoid introducing unnecessary framework layers
- keep output schema minimal
- design for later HTTP serialization
- do not couple prompt assembly to API transport more than necessary
