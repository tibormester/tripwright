from __future__ import annotations


def build_research_planner_prompt(
    *,
    place_name: str,
    area_name: str,
    neighborhood: str,
    prior_steps: list[dict[str, str]],
    snippets: list[dict[str, str]],
    remaining_steps: int,
) -> str:
    step_text = "\n".join(
        f"- step {index + 1}: action={step.get('action', '')}, query={step.get('query', '')}, notes={step.get('notes', '')}"
        for index, step in enumerate(prior_steps)
    ) or "- none"
    snippet_text = "\n".join(
        f"- title={snippet.get('title', '')} | url={snippet.get('url', '')} | snippet={snippet.get('snippet', '')}"
        for snippet in snippets[-8:]
    ) or "- none"

    return f"""
You are planning capped local-flavor research for a travel narrative game.

Target lodging: {place_name}
Area target: {area_name}
Neighborhood hint: {neighborhood or 'unknown'}
Remaining steps: {remaining_steps}

Research goal:
- learn the local vibe, social texture, common hangouts, gentle sayings/slang if available, and traveler-relevant flavor
- avoid overclaiming
- prefer specific but soft observations
- if enough evidence exists, finish instead of searching more

Previous steps:
{step_text}

Search snippets collected so far:
{snippet_text}

Return JSON only with this exact shape:
{{
  "action": "search" | "finish",
  "query": "string",
  "notes": "string"
}}

Rules:
- Use action=search only if another search would materially improve the report.
- Use action=finish when the available snippets are sufficient or no better query is obvious.
- Queries should be short and web-searchable.
- Prefer queries like: vibe of <area>, what is <area> known for, cafes/bookstores/parks in <area>, local slang in <city>.
""".strip()


def build_research_summary_prompt(
    *,
    place_name: str,
    area_name: str,
    neighborhood: str,
    snippets: list[dict[str, str]],
) -> str:
    snippet_text = "\n".join(
        f"- title={snippet.get('title', '')} | url={snippet.get('url', '')} | snippet={snippet.get('snippet', '')}"
        for snippet in snippets[:16]
    ) or "- none"

    return f"""
You are summarizing lightweight public web research for a travel narrative game.

Target lodging: {place_name}
Area target: {area_name}
Neighborhood hint: {neighborhood or 'unknown'}

Evidence snippets:
{snippet_text}

Return JSON only with this exact shape:
{{
  "area_summary": "string",
  "tone_keywords": ["string"],
  "local_sayings": ["string"],
  "demographic_archetypes": ["string"],
  "common_hobbies": ["string"],
  "social_norms": ["string"],
  "lodging_context": "string",
  "destination_recommendation_notes": ["string"]
}}

Rules:
- Keep claims soft, grounded, and non-hypey.
- If evidence is weak, use cautious wording.
- local_sayings may be empty if evidence is weak.
- Keep each list compact and useful.
""".strip()
