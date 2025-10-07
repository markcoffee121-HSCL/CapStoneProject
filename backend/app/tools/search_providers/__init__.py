from __future__ import annotations
from typing import Callable, List, Optional, Dict, Any
import asyncio
from ...config import settings
from .tavily import tavily_search
from .duckduckgo import ddg_search
from .serpapi import serpapi_search

# All providers must expose this signature:
# async def search(query: str, max_results: int, domains: Optional[List[str]]) -> List[Dict[str, Any]]

def _with_domains(query: str, domains: Optional[List[str]]) -> str:
    if not domains:
        return query
    # Add a simple OR sites clamp to steer most engines
    sites = " OR ".join([f"site:{d}" for d in domains])
    return f"({query}) ({sites})"

def get_search_provider() -> Callable[[str, int, Optional[List[str]]], "asyncio.Future"]:
    name = (settings.SEARCH_PROVIDER or "tavily").lower().strip()
    if name == "tavily":
        api_key = settings.TAVILY_API_KEY
        async def _search(query: str, max_results: int, domains: Optional[List[str]]):
            return await tavily_search(query, max_results=max_results, domains=domains, api_key=api_key)
        return _search

    if name == "serpapi":
        api_key = settings.SERPAPI_API_KEY
        async def _search(query: str, max_results: int, domains: Optional[List[str]]):
            q = _with_domains(query, domains)
            return await serpapi_search(q, max_results=max_results, api_key=api_key)
        return _search

    # default: duckduckgo (no key)
    async def _search(query: str, max_results: int, domains: Optional[List[str]]):
        q = _with_domains(query, domains)
        return await ddg_search(q, max_results=max_results)
    return _search
