from __future__ import annotations
from typing import List, Dict, Any, Optional
import httpx

async def serpapi_search(  # Changed from 'search' to 'serpapi_search'
    query: str,
    max_results: int = 5,
    api_key: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Google results via SerpAPI.
    """
    if not api_key:
        return []

    params = {
        "engine": "google",
        "q": query,
        "num": min(max_results * 2, 20),
        "api_key": api_key,
    }
    
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get("https://serpapi.com/search.json", params=params)
        r.raise_for_status()
        data = r.json()

    out: List[Dict[str, Any]] = []
    for it in data.get("organic_results", []):
        url = it.get("link")
        if not url:
            continue
        out.append({
            "title": it.get("title", ""),
            "url": url,
            "snippet": it.get("snippet", ""),
        })
    return out[:max_results]