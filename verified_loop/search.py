"""Search + fetch behind one interface, so Tavily/Exa/Brave are swappable and
tests run offline against a fixture."""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import Protocol


@dataclass
class Source:
    url: str
    title: str
    text: str  # extracted main content


class SearchTool(Protocol):
    async def search(self, query: str, k: int = 3) -> list[Source]: ...


class TavilySearch:
    """Real search via Tavily (free tier). Needs TAVILY_API_KEY."""

    def __init__(self) -> None:
        self._key = os.environ.get("TAVILY_API_KEY")

    async def search(self, query: str, k: int = 3) -> list[Source]:
        import httpx  # lazy

        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": self._key,
                    "query": query,
                    "max_results": k,
                    "include_raw_content": True,
                },
            )
            r.raise_for_status()
            data = r.json()
        return [
            Source(
                url=item["url"],
                title=item.get("title", ""),
                text=(item.get("raw_content") or item.get("content") or "")[:8000],
            )
            for item in data.get("results", [])
        ]


class FixtureSearch:
    """Offline search that returns canned sources — used by --replay and tests."""

    def __init__(self, by_query: dict[str, list[Source]] | None = None) -> None:
        self._by_query = by_query or {}

    async def search(self, query: str, k: int = 3) -> list[Source]:
        await asyncio.sleep(0)  # keep the async contract
        for needle, sources in self._by_query.items():
            if needle.lower() in query.lower():
                return sources[:k]
        return []
