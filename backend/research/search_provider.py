from __future__ import annotations

from dataclasses import dataclass
import logging
import time

logger = logging.getLogger(__name__)

DDG_HTML_SEARCH_URL = "https://html.duckduckgo.com/html/"
DEFAULT_SEARCH_USER_AGENT = "tripwright/0.1 (research prototype)"


@dataclass
class SearchSnippet:
    title: str
    url: str
    snippet: str

    def to_dict(self) -> dict[str, str]:
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
        }


class DuckDuckGoSearchProvider:
    def __init__(self, *, timeout_seconds: float = 10.0, user_agent: str = DEFAULT_SEARCH_USER_AGENT, max_retries: int = 0) -> None:
        self.timeout_seconds = timeout_seconds
        self.user_agent = user_agent
        self.max_retries = max_retries

    def search(self, query: str, max_results: int = 5) -> list[SearchSnippet]:
        cleaned_query = query.strip()
        if not cleaned_query:
            return []

        import requests
        from bs4 import BeautifulSoup

        last_error: Exception | None = None
        response = None
        for attempt in range(self.max_retries + 1):
            try:
                response = requests.post(
                    DDG_HTML_SEARCH_URL,
                    timeout=self.timeout_seconds,
                    headers={"User-Agent": self.user_agent},
                    data={"q": cleaned_query},
                )
                response.raise_for_status()
                if attempt:
                    logger.info("duckduckgo search recovered | query=%s | attempt=%s", cleaned_query, attempt + 1)
                break
            except Exception as exc:
                last_error = exc
                logger.warning("duckduckgo search failed | query=%s | attempt=%s/%s | error=%s", cleaned_query, attempt + 1, self.max_retries + 1, exc)
                if attempt < self.max_retries:
                    time.sleep(min(0.5 * (attempt + 1), 1.5))
        if response is None:
            if last_error is not None:
                raise last_error
            return []

        soup = BeautifulSoup(response.text, "html.parser")

        results: list[SearchSnippet] = []
        for result in soup.select(".result"):
            title_node = result.select_one(".result__title a") or result.select_one("a.result__a")
            snippet_node = result.select_one(".result__snippet")
            if title_node is None:
                continue

            title = " ".join(title_node.stripped_strings)
            url = str(title_node.get("href") or "").strip()
            snippet = " ".join(snippet_node.stripped_strings) if snippet_node else ""
            if not title or not url:
                continue

            results.append(SearchSnippet(title=title, url=url, snippet=snippet))
            if len(results) >= max_results:
                break

        return results
