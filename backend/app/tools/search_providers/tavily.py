from __future__ import annotations
import httpx
from typing import Any, Dict, List, Optional

API_URL = "https://api.tavily.com/search"

async def tavily_search(
    query: str,
    *,
    max_results: int = 6,
    domains: Optional[List[str]] = None,
    api_key: Optional[str] = None,
) -> List[Dict[str, Any]]:
    if not api_key:
        # graceful fallback: behave like empty results when key isn't set
        return []

    payload: Dict[str, Any] = {
        "api_key": api_key,
        "query": query,
        "search_depth": "advanced" if max_results > 5 else "basic",
        "max_results": max_results,
        "include_answer": False,
        "include_images": False,
    }
    if domains:
        payload["include_domains"] = domains

    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(API_URL, json=payload)
        r.raise_for_status()
        data = r.json()

    results: List[Dict[str, Any]] = []
    for item in data.get("results", []):
        results.append({
            "url": item.get("url"),
            "title": item.get("title") or item.get("url"),
            "snippet": item.get("content") or "",
            "score": item.get("score"),
            "engine": "tavily",
        })
    return results[:max_results]
