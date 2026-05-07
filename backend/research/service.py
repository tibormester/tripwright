from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Any

from ..config import AppConfig
from ..location.models import LocationContext
from ..npc_agent.openai_utils import load_env_file
from .models import ResearchReport
from .prompts import build_research_planner_prompt, build_research_summary_prompt
from .search_provider import DuckDuckGoSearchProvider, SearchSnippet

logger = logging.getLogger(__name__)

DEFAULT_RESEARCH_MODEL = "gpt-4o-mini"
DEFAULT_AGENTIC_STEPS = 3


@dataclass
class ResearchStep:
    action: str
    query: str
    notes: str

    def to_dict(self) -> dict[str, str]:
        return {"action": self.action, "query": self.query, "notes": self.notes}


class ResearchService:
    def __init__(
        self,
        config: AppConfig | None = None,
        *,
        search_provider: DuckDuckGoSearchProvider | None = None,
    ) -> None:
        self.config = config or AppConfig.from_env()
        self.search_provider = search_provider or DuckDuckGoSearchProvider(
            timeout_seconds=self.config.provider_timeout_seconds,
            max_retries=self.config.provider_max_retries,
        )
        self.max_agent_steps = max(1, int(getattr(self.config, "research_max_agent_steps", DEFAULT_AGENTIC_STEPS)))

    def research_area(self, location_context: LocationContext) -> ResearchReport:
        started_at = time.perf_counter()
        if not self.config.search_enabled:
            logger.info("research skipped | reason=search_disabled")
            return self._build_fallback_report(location_context, snippets=[])

        place_name = location_context.canonical_name or location_context.input_value
        area_name = _build_area_name(location_context)
        collected_snippets: list[SearchSnippet] = []
        steps: list[ResearchStep] = []
        seen_queries: set[str] = set()

        logger.info("research start | place=%s | area=%s | max_steps=%s", place_name, area_name, self.max_agent_steps)

        for step_index in range(self.max_agent_steps):
            remaining_steps = self.max_agent_steps - step_index
            planner_decision = self._plan_next_step(
                place_name=place_name,
                area_name=area_name,
                neighborhood=location_context.neighborhood,
                steps=steps,
                snippets=collected_snippets,
                remaining_steps=remaining_steps,
            )
            steps.append(planner_decision)

            logger.info(
                "research step | step=%s | action=%s | query=%s | notes=%s",
                step_index + 1,
                planner_decision.action,
                planner_decision.query,
                planner_decision.notes,
            )
            if planner_decision.action == "finish":
                break

            query = planner_decision.query.strip()
            if not query or query.lower() in seen_queries:
                continue
            seen_queries.add(query.lower())

            try:
                new_results = self.search_provider.search(query, max_results=5)
            except Exception as exc:
                logger.warning("research search failed | query=%s | error=%s", query, exc)
                new_results = []
            logger.info("research search results | query=%s | count=%s", query, len(new_results))
            collected_snippets.extend(new_results)

        if not collected_snippets:
            logger.info("research fallback | reason=no_snippets")
            return self._build_fallback_report(location_context, snippets=[])

        summary_payload = self._summarize_research(
            place_name=place_name,
            area_name=area_name,
            neighborhood=location_context.neighborhood,
            snippets=collected_snippets,
        )
        if summary_payload is None:
            logger.info("research fallback | reason=summary_unavailable | snippet_count=%s", len(collected_snippets))
            return self._build_fallback_report(location_context, snippets=collected_snippets)

        report = ResearchReport(
            area_summary=str(summary_payload.get("area_summary", "")),
            tone_keywords=_normalize_string_list(summary_payload.get("tone_keywords", [])),
            local_sayings=_normalize_string_list(summary_payload.get("local_sayings", [])),
            demographic_archetypes=_normalize_string_list(summary_payload.get("demographic_archetypes", [])),
            common_hobbies=_normalize_string_list(summary_payload.get("common_hobbies", [])),
            social_norms=_normalize_string_list(summary_payload.get("social_norms", [])),
            lodging_context=str(summary_payload.get("lodging_context", "")),
            destination_recommendation_notes=_normalize_string_list(summary_payload.get("destination_recommendation_notes", [])),
            sources=[{"url": snippet.url, "title": snippet.title} for snippet in collected_snippets],
            raw_snippets=[snippet.to_dict() for snippet in collected_snippets],
        )
        logger.info(
            "research complete | place=%s | snippets=%s | tone_keywords=%s | duration_ms=%s",
            place_name,
            len(collected_snippets),
            ", ".join(report.tone_keywords[:4]),
            int((time.perf_counter() - started_at) * 1000),
        )
        return report

    def _plan_next_step(
        self,
        *,
        place_name: str,
        area_name: str,
        neighborhood: str,
        steps: list[ResearchStep],
        snippets: list[SearchSnippet],
        remaining_steps: int,
    ) -> ResearchStep:
        prompt = build_research_planner_prompt(
            place_name=place_name,
            area_name=area_name,
            neighborhood=neighborhood,
            prior_steps=[step.to_dict() for step in steps],
            snippets=[snippet.to_dict() for snippet in snippets],
            remaining_steps=remaining_steps,
        )
        payload = self._call_json_model(prompt)
        if payload is None:
            fallback_queries = _default_queries(area_name, neighborhood)
            query = fallback_queries[min(len(steps), len(fallback_queries) - 1)]
            logger.info("research planner fallback | query=%s", query)
            return ResearchStep(action="search", query=query, notes="fallback query")

        action = str(payload.get("action", "search")).strip().lower() or "search"
        if action not in {"search", "finish"}:
            action = "search"
        return ResearchStep(
            action=action,
            query=str(payload.get("query", "")).strip(),
            notes=str(payload.get("notes", "")).strip(),
        )

    def _summarize_research(
        self,
        *,
        place_name: str,
        area_name: str,
        neighborhood: str,
        snippets: list[SearchSnippet],
    ) -> dict[str, Any] | None:
        prompt = build_research_summary_prompt(
            place_name=place_name,
            area_name=area_name,
            neighborhood=neighborhood,
            snippets=[snippet.to_dict() for snippet in snippets],
        )
        return self._call_json_model(prompt)

    def _call_json_model(self, prompt: str) -> dict[str, Any] | None:
        try:
            from openai import OpenAI
        except ImportError:
            return None

        load_env_file()
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return None

        client = OpenAI(api_key=api_key)
        model_name = os.getenv("OPENAI_MODEL", DEFAULT_RESEARCH_MODEL)

        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
            )
        except Exception:
            return None

        raw_content = response.choices[0].message.content or "{}"
        try:
            payload = json.loads(raw_content)
        except json.JSONDecodeError:
            return None
        return payload if isinstance(payload, dict) else None

    def _build_fallback_report(
        self,
        location_context: LocationContext,
        *,
        snippets: list[SearchSnippet],
    ) -> ResearchReport:
        area_name = _build_area_name(location_context)
        tone_keywords = [keyword for keyword in [location_context.neighborhood, location_context.city, "walkable", "local"] if keyword]
        destination_notes = [
            f"Prefer nearby places that feel plausible for a traveler staying around {area_name}.".strip(),
            "Recommendations should sound grounded and low-pressure rather than touristy.",
        ]
        return ResearchReport(
            area_summary=f"The area around {area_name} seems suitable for low-key traveler exploration, with emphasis on nearby walkable stops and neighborhood texture.".strip(),
            tone_keywords=tone_keywords[:4],
            local_sayings=[],
            demographic_archetypes=["locals moving through their routines", "service workers used to visitors"],
            common_hobbies=["coffee breaks", "reading", "short neighborhood walks"],
            social_norms=["keep recommendations practical", "favor calm and approachable local spots"],
            lodging_context=f"Use the lodging as the player's anchor and frame nearby suggestions as easy first stops from {location_context.canonical_name or location_context.input_value}.".strip(),
            destination_recommendation_notes=destination_notes,
            sources=[{"url": snippet.url, "title": snippet.title} for snippet in snippets],
            raw_snippets=[snippet.to_dict() for snippet in snippets],
        )


def _build_area_name(location_context: LocationContext) -> str:
    parts = [location_context.neighborhood, location_context.city, location_context.region]
    return ", ".join(part for part in parts if part) or location_context.canonical_name or location_context.input_value


def _default_queries(area_name: str, neighborhood: str) -> list[str]:
    area = neighborhood or area_name
    return [
        f"vibe of {area}",
        f"what is {area_name} known for",
        f"cafes bookstores parks in {area_name}",
    ]


def _normalize_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    output: list[str] = []
    for item in value:
        text = str(item).strip()
        if text:
            output.append(text)
    return output
