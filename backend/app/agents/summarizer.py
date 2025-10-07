from __future__ import annotations
import asyncio
from ..observability.events import bus, make_event
from ..graph.state import GraphState

def _shorten(s: str, n: int = 500) -> str:
    s = " ".join(s.split())
    return s[: n - 3] + "..." if len(s) > n else s

async def summarizer_node(state: GraphState) -> GraphState:
    run_id = state.get("run_id", "unknown")
    await bus.publish(make_event(run_id, "summarize", "started", agent="summarizer"))

    limits = state.get("limits", {})
    target_words = int(limits.get("summary_words", 200))
    bullet_chars = max(80, int(target_words * 6 * 0.6))  # rough char estimate

    k = int(state.get("max_sources", 6))
    notes = []
    for d in state.get("docs", [])[: max(1, k)]:
        notes.append({
            "url": d["url"],
            "bullets": [
                _shorten(d.get("content", ""), bullet_chars),
                f"Title: {d.get('title','')}",
            ],
        })

    await bus.publish(
        make_event(run_id, "summarize", "completed", agent="summarizer", data={"notes": len(notes), "target_words": target_words})
    )
    return {**state, "notes": notes}
