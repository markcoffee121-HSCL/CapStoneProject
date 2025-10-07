from __future__ import annotations
from typing import Any, Dict, List, Optional
import asyncio
from duckduckgo_search import DDGS

async def ddg_search(query: str, *, max_results: int = 6) -> List[Dict[str, Any]]:
    # DDG is sync; run it in a thread to avoid blocking the loop
    def _run():
        with DDGS() as ddgs:
            res = ddgs.text(
                keywords=query,
                region="wt-wt",
                safesearch="moderate",
                timelimit=None,
                max_results=max_results,
            )
            return list(res) if res else []

    items = await asyncio.to_thread(_run)
    results: List[Dict[str, Any]] = []
    for item in items:
        results.append({
            "url": item.get("href") or item.get("url"),
            "title": item.get("title") or item.get("url"),
            "snippet": item.get("body") or item.get("snippet") or "",
            "engine": "duckduckgo",
        })
    return results[:max_results]
