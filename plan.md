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
  "flags": ["goal_progress_check_in_started"]
}
```

Flags act like lightweight tool calls.

Examples:
- `goal_met_check_in`
- `goal_met_offer_alternative`
- `goal_met_learn_preference`
- `conversation_end`

We will not implement provider-specific tool calling yet.

### 4. Context Management
Do not overengineer memory yet.

Assumption:
- conversations will be short
- full dialogue history can be passed directly for now

That means v1 can simply include the full recent conversation in state.

### 5. Realism Constraints
The NPC prompt should explicitly enforce conversational realism.

Important constraints:
- stay in character
- speak like a person, not an assistant
- keep responses concise
- ask at most one meaningful follow-up at a time
- do not narrate the user's actions
- use local flavor naturally
- do not dump too much information at once
- preserve emotional and personality consistency

---

## Architecture

The implementation should follow single-responsibility principles.

### Core Pieces

#### 1. Conversation State
Responsibility:
- hold all mutable conversation data

Possible contents:
- location
- static scene text
- NPC profile data
- overt goals
- subtle goals
- dialogue history
- turn count
- active flags
- completed goals

This should be serializable to JSON.

#### 2. NPC Profile
Responsibility:
- define the specific NPC identity and behavior inputs

This is the content layer, not the assembly layer.

It may include:
- role
- personality traits
- emotional traits
- physical presentation notes
- beliefs / opinions
- overt goals
- subtle goals
- speaking style
- location-specific flavor

For v1, this can be static.

Later, parts of it may be enriched from web search or location research.

#### 3. Prompt Builder
Responsibility:
- assemble the final prompt from reusable sections and runtime state

The prompt builder is the structure layer.

It should define:
- what goes in the system prompt
- how NPC profile fields are injected
- how conversation state is injected
- how output rules are expressed
- how JSON response requirements are expressed

### Clarifying the distinction: NPC Profile vs Prompt Builder
The overlap is real, but the separation should be:

- **NPC Profile** = the character-specific content
- **Prompt Builder** = the logic that turns content + state into a final prompt

Analogy:
- profile = ingredients
- prompt builder = recipe

So the prompt builder should not own the NPC's personality itself.
It should consume an NPC profile and a conversation state and output a prompt.

In code terms, the NPC profile does **not** need to extend the prompt builder.
A cleaner design is:
- `NPCProfile` stores the data
- `PromptBuilder` consumes `NPCProfile` + `ConversationState`

If later we want profile generation, that should be handled by a separate component rather than collapsing profile and prompt builder together.

#### 4. Agent Builder
Responsibility:
- prepare and maintain the runtime context needed by the agent

This is the orchestration layer for setup.

It should handle things like:
- creating a new conversation state
- injecting static narration into the initial history/context
- attaching the NPC profile
- preparing the agent for use

This is where context assembly decisions belong, not inside the low-level state object.

#### 5. Agent
Responsibility:
- execute one NPC turn

The agent should:
- accept conversation state and new user input
- update dialogue history
- call the prompt builder
- send the prompt to OpenAI
- parse JSON response
- append the NPC reply to history
- surface dialogue / thoughts / flags back to the caller

This should be the main behavioral unit.

---

## Proposed File Structure

Exact filenames can still change, but the responsibilities should look like this:

- `agent.py`
  - the core NPC agent turn logic

- `agent_builder.py`
  - creates and prepares an agent with its conversation context

- `prompt_builder.py`
  - builds prompts from profile + state

- `state.py`
  - conversation state structures / serialization helpers

- `npc_profile.py`
  - NPC profile structures and static example profile(s)

Avoid naming a file `models.py` to reduce confusion with API/client model abstractions.

---

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

---

## Initial Data Shape

### Conversation State (conceptual)
```json
{
  "location": "grand hotel",
  "scene_intro": {
    "setting": "...",
    "npc_intro": "...",
    "first_contact": "..."
  },
  "npc_profile": {
    "name": "...",
    "role": "...",
    "personality": [],
    "overt_goals": [],
    "subtle_goals": []
  },
  "dialogue_history": [
    {"speaker": "narrator", "text": "..."},
    {"speaker": "npc", "text": "..."},
    {"speaker": "user", "text": "..."}
  ],
  "completed_goals": [],
  "flags": [],
  "turn_count": 0
}
```

This shape does not need to be final, but it should remain easy to serialize.

---

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

### Flag Strategy
When the model believes a goal has been advanced or completed, it should emit a matching flag.

Examples:
- `goal_met_greet_guest`
- `goal_met_identify_need`
- `goal_met_offer_local_recommendation`
- `goal_met_learn_user_vibe`
- `conversation_end`

Application logic can then search flags rather than requiring formal tool-calling support.

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

### Phase 1
- define state shape
- define NPC profile shape
- define prompt builder
- define agent builder
- define agent turn execution

### Phase 2
- wire to OpenAI API
- validate JSON outputs
- basic flag handling

### Phase 3
- add one concrete example NPC
- test multi-turn conversation behavior
- refine prompt realism constraints

### Phase 4
- prepare for later HTTP integration
- optionally add profile enrichment pipeline

---

## v1 Success Criteria

The prototype is successful if:
- it can build a JSON-serializable conversation state
- it can generate NPC dialogue in character
- it returns JSON with `dialogue`, `thoughts`, and `flags`
- it can track basic goal completion through flags
- prompt construction remains modular
- responsibilities are separated cleanly across components

---

## Notes for Coding

- prioritize readability over abstraction
- keep class responsibilities narrow
- avoid introducing unnecessary framework layers
- keep output schema minimal
- design for later HTTP serialization
- do not couple prompt assembly to API transport more than necessary
