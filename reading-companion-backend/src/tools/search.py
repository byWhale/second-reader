"""Tavily search tool definition with LangGraph tool decorator."""

from typing import Optional, TypedDict, Union

from langchain_core.tools import tool
from tavily import TavilyClient

from src.config import get_tavily_api_key
from src.reading_core.runtime_contracts import CurrentReadingProblemCode


class TavilySearchResult(TypedDict):
    """Tavily search result type"""
    title: str
    url: str
    content: str
    score: Optional[float]


_SEARCH_TIMEOUT_SECONDS = 20


def classify_search_problem(message: str) -> CurrentReadingProblemCode:
    """Map one Tavily/network failure into a stable runtime problem code."""
    lowered = str(message or "").lower()
    if any(token in lowered for token in ("timed out", "timeout", "read timeout", "deadline exceeded")):
        return "search_timeout"
    if any(token in lowered for token in ("authentication", "unauthorized", "forbidden", "invalid api key", "api key not configured")):
        return "search_auth"
    if any(token in lowered for token in ("quota", "insufficient", "billing", "credit balance", "rate limit", "429")):
        return "search_quota"
    return "network_blocked"


@tool
def search_web(query: str, max_results: int = 5) -> list[dict]:
    """Search the web for relevant information.

    Use this tool when you need to verify facts, find source attributions,
    or gather background information for quote expansion.

    Args:
        query: The search query string
        max_results: Maximum number of results to return (default: 5)

    Returns:
        List of search results with title, url, content, and score
    """
    api_key = get_tavily_api_key()
    if not api_key:
        error = "TAVILY_API_KEY not configured"
        return [{"error": error, "problem_code": classify_search_problem(error)}]

    client = TavilyClient(api_key=api_key)
    try:
        response = client.search(
            query=query,
            max_results=max_results,
            timeout=_SEARCH_TIMEOUT_SECONDS,
        )
    except Exception as exc:  # pragma: no cover - integration/runtime behavior
        error = str(exc)
        return [{"error": error, "problem_code": classify_search_problem(error)}]

    results = []
    for result in response.get("results", []):
        results.append({
            "title": result.get("title", ""),
            "url": result.get("url", ""),
            "content": result.get("content", ""),
            "score": result.get("score"),
        })

    return results


# Keep backward compatibility
def create_search_tool(api_key: Optional[str] = None):
    """Create Tavily search tool (legacy function for compatibility).

    Args:
        api_key: Tavily API key (optional, uses config if not provided)

    Returns:
        Search function
    """
    if api_key is None:
        api_key = get_tavily_api_key()

    client = TavilyClient(api_key=api_key)

    def search(query: str, max_results: int = 5) -> list[TavilySearchResult]:
        """Search relevant content.

        Args:
            query: Search query
            max_results: Max results

        Returns:
            Search results list
        """
        response = client.search(
            query=query,
            max_results=max_results,
            timeout=_SEARCH_TIMEOUT_SECONDS,
        )
        return [
            TavilySearchResult(
                title=result.get("title", ""),
                url=result.get("url", ""),
                content=result.get("content", ""),
                score=result.get("score"),
            )
            for result in response.get("results", [])
        ]

    return search
