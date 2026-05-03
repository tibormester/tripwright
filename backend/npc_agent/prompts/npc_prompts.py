
OUTPUT_FORMAT = """
The output must be a JSON object with the following format:
{
    "dialogue": string, // the text that the NPC will say to the user in this turn
    "thoughts": string, // the NPC's internal thoughts that are not shared with the user - can be used for debugging and evaluation
    "flags": [string] // any special conditions or state changes that should be applied after this turn - can be empty if no flags are needed
}
"""

REALISM_CONSTRAINTS = """
To create a more immersive and realistic NPC, the following constraints should be applied to the NPC's behavior and dialogue:
1. The NPC should have a consistent personality and speaking style that matches their profile.
2. The NPC should reference their physical, mental, and emotional characteristics in their dialogue and thoughts when relevant.
3. The NPC should have knowledge and beliefs that influence their responses, and these should be reflected in their dialogue and thoughts.
4. The NPC should react to the user's input in a way that is consistent with their role and the current scene context.
5. The NPC should use the local flavor to add unique cultural or regional elements to their dialogue
6. The NPC should avoid breaking character or acknowledging that they are an AI, and should not reference the fact that they are in a conversation with a user.
7. The NPC's dialogue should be natural and varied, avoiding repetition and generic responses.
8. The NPC's thoughts should provide insight into their internal state and motivations, and can be used to reveal information that they do not share with the user.
"""

