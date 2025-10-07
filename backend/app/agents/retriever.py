from __future__ import annotations
import asyncio
from typing import List, Dict
import httpx, trafilatura
from bs4 import BeautifulSoup
from ..observability.events import bus, make_event
from ..graph.state import GraphState

UA = "Mozilla/5.0 (HSCL-Capstone Fetcher)"

def _extract_text(html: str) -> str:
    txt = trafilatura.extract(html, include_comments=False) or ""
    if not txt:
        soup = BeautifulSoup(html, "lxml")
        txt = soup.get_text(" ", strip=True)
    return " ".join(txt.split())

async def _fetch(url: str, client: httpx.AsyncClient) -> Dict | None:
    try:
        r = await client.get(url, headers={"User-Agent": UA})
        r.raise_for_status()
        text = _extract_text(r.text)
        if len(text) < 400:
            return None
        return {"url": url, "title": "", "content": text}
    except Exception:
        return None

async def retriever_node(state: GraphState) -> GraphState:
    run_id = state.get("run_id", "unknown")
    await bus.publish(make_event(run_id, "retrieve", "started", agent="retriever"))

    limits = state.get("limits", {})
    timeout = int(limits.get("fetch_timeout", 20))

    k = int(state.get("max_sources", 6))
    results = state.get("results", [])[: max(1, k * 2)]
    urls = [r["url"] for r in results if r.get("url")]

    docs: List[Dict] = []
    async with httpx.AsyncClient(timeout=timeout) as client:
        tasks = [_fetch(u, client) for u in urls]
        for coro in asyncio.as_completed(tasks):
            d = await coro
            if d:
                docs.append(d)
            if len(docs) >= k:
                break

    await bus.publish(make_event(run_id, "retrieve", "completed", agent="retriever", data={"docs": len(docs)}))
    return {**state, "docs": docs}
