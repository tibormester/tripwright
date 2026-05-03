Prototype a conversational agent with personality and subtle goals.

- Want the agent prompt to be modular:
prefix + dialogue history + suffix -> llm

prefix = role, output template, personality, overt goals, subtle goals, tool calls
        personality = universal stuff: physical traits, mental traits, emotional traits.
                    = cultural stuff: unique to location, inspired by archetypes - want to research the location and use that to make location specific personalities if possible.
                    = opinions / beliefs.
                    we can experiment with what works here and doesn't
        overt goals:  aligned with their job at the location: e.x. receptionist faciliting check in, but rooms not ready, so attempting to offer alternatives: drop your bags off, theres a cafe down the street.
        subtle goals: dispensing some local / cultural knowledge - this is a local specifialty or festival or heritage sight, are you planning on trying it out etc...?  ascertaining preferences, theres a few different cafes depending on the vibe. list a few options vibe.

suffix = tool calls, output template

dialogue history: 
    step 0: narrator describing the setting. - walking into a grand hotel
        subtle goal - provide a visual description sufficient for imagining the scene
    step 1: narrator describing the npc. - a guy looking energetic sitting at the front desk
        subtle goal - provide a visual description sufficient for imagining the npc
    step 2: narrator describing the npc noticing the character. - he looks onto you as you enter through the front door, you're exhausted from your red eye flight, but his energy is contagious
        subtle goal - make a spark/excuse for interesting small talk to build off of
                    

    step n: npc talks to you

    step n+1: you respond to the npc

    step n+2: npc checks if its goals have been accomplished based on your response, if not asks followups, if accomplished, emits flag that goal is finished. If all goals are finished, then does a farewell dialogue response.

    step 4: narrator describes the scene transition.