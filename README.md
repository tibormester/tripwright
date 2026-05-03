# tripwright
A narrative travel dialogue game with staged NPC encounters.

An AI-driven cultural discovery experience where each local NPC helps shape the player’s preferences and route.

## Design Decisions

- Fixed route (or semi-fixed) Not open world simulation - minimize complexity
    check-in -> coffee -> cultural attraction -> gas station -> dinner
- NPCs are the core content unity
    Their prompts are dynamically constructed with different modules
        - they have an identity and personality
            - identity needs to big and random and opinionated enough so they dont just sound like a tour guide
        - a unique local perspective
            - part of their job and personality should inform the kind of local perspective they have
        - a stage objective: making small talk, revealing the culture and exploring the users preferences, then getting the users next choice in destination.

- Preferences are captured progressively and subtly through dialague during the immersive experience

- Maybe a conversation starter engine that looks at the transitions between the scenes, describes the user as they enter the scene, giving the npc a way to anchor the conversation more naturally instead of cold approaches that feel unnatural.

- similar purpose. Npc conversation starter engine, give them a reason to want to start a conversation, probably just boredom? mostly out of diligence for their job? idrk...

- Make a visual description in text of the npcs, but also generate a headshot and display it on the front end so that way the experience feels more alive. 

- player character headshot, is it needed and how? let them upload something or describe themselves and use the npc pipeline.

- final summary that prints the preferences extracted and summarized - letting the player know what they like because they never know themselves.

## Getting started

backend is started with:
```
python backend/app.py
```
client is started with:
```
node client/client.js
```

## Features TODO:

1. Back end
    - server routing logic (deceptively simple)
        - create session request
        - play session request
        - stream dialogue back
        - send headshot image back (probably comes with the session state update when the scene changes)
        - send session state updates (server should be stateless, all game state is sent to client and they send it back, no caching, adds too much technical requirements)

    - game state management
        - facilitate initil 
        - determine which scene/npc is the current one

2. Front end
    - server routing logic
        - call the right end points based on state
        - recieve streamed dialogue
        - receieve session state updates and respond visually
    - state management (simple just store it in a variable...)
    - lifecycle events:
        - by default create a new session on start
        - when the npc changes, wipe the dialogue and restart
        - provide a few utilities for basic stuff like restarting or exiting.


