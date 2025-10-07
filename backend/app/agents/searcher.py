from __future__ import annotations
import asyncio, re
from urllib.parse import urlparse
from typing import List, Dict, Optional
from ..observability.events import bus, make_event
from ..config import settings
from ..graph.state import GraphState
from ..tools.search_providers import get_search_provider
from ..tools.search_providers.duckduckgo import ddg_search  # fallback

def _domain(u: str) -> str:
    host = (urlparse(u).hostname or "").lower()
    if host.startswith("www:") or host.startswith("www."):
        host = host.split(".", 1)[-1]
    return host

# CJK quick check
_CJK = re.compile(r"[\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af]")

def _looks_english(text: str, url: str) -> bool:
    if _CJK.search(text or ""):
        return False
    h = _domain(url)
    if h.endswith((".cn", ".jp", ".kr", ".ru")):
        return False
    return True

async def _provider_search(query: str, k: int, domains: Optional[List[str]]) -> List[Dict]:
    search_fn = get_search_provider()
    try:
        res = await search_fn(query, max_results=k, domains=domains)
        return [
            {"title": r.get("title", ""), "url": r.get("url", "") or r.get("link", ""), "snippet": r.get("snippet", "")}
            for r in res
        ]
    except Exception:
        # fallback to DDG (no key)
        res = await ddg_search(query, max_results=k)
        return [
            {"title": r.get("title", ""), "url": r.get("url", "") or r.get("link", ""), "snippet": r.get("snippet", "")}
            for r in res
        ]

async def searcher_node(state: GraphState) -> GraphState:
    run_id = state.get("run_id", "unknown")
    q = state.get("topic", "")
    k = int(state.get("max_sources", 6))
    domains = state.get("domains") or None

    await bus.publish(make_event(run_id, "search", "started", agent="searcher"))  # Only once!

    raw = await _provider_search(q, max(10, k * 2), domains)  # get a larger candidate pool

    # de-dup by domain
    seen = set()
    dedup: List[Dict] = []
    for item in raw:
        u = item.get("url") or ""
        if not u:
            continue
        d = _domain(u)
        if d in seen:
            continue
        seen.add(d)
        dedup.append(item)

    # prefer English if configured
    prefer_lang = (settings.PREFER_LANG or "").lower()
    out: List[Dict] = []
    if prefer_lang == "en":
        for item in dedup:
            if _looks_english(item.get("snippet", ""), item["url"]):
                out.append(item)
                if len(out) >= k:
                    break
        if len(out) < k:
            for item in dedup:
                if item not in out:
                    out.append(item)
                    if len(out) >= k:
                        break
    else:
        out = dedup[:k]

    await bus.publish(make_event(run_id, "search", "completed", agent="searcher", data={"count": len(out)}))
    return {**state, "results": out}