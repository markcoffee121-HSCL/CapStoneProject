from __future__ import annotations
from ..observability.events import bus, make_event
from ..config import settings
from ..graph.state import GraphState
from typing import List, Dict

def _mk_report(topic: str, notes: List[Dict], model: str, provider: str) -> str:
    lines = []
    lines.append(f"# Research Brief: {topic or 'Untitled'}")
    lines.append("")
    lines.append("**Executive Summary**")
    lines.append("")
    if not notes:
        lines.append("_No sources retrieved._")
    else:
        lines.append("This brief synthesizes key points from the retrieved sources.")
    lines.append("")
    lines.append("## Key Takeaways")
    if not notes:
        lines.append("- No findings available.")
    else:
        # one bullet per source (first line) + include title/url
        for n in notes:
            bullets = n.get("bullets") or []
            head = bullets[0] if bullets else ""
            url = n.get("url", "")
            lines.append(f"- {head} ({url})")
    lines.append("")
    lines.append("## Citations")
    if not notes:
        lines.append("- (none)")
    else:
        for n in notes:
            url = n.get("url") or ""
            if url:
                lines.append(f"- {url}")
    lines.append("")
    lines.append(f"_Model: {model} · Search: {provider}_")
    return "\n".join(lines)

async def synthesizer_node(state: GraphState) -> GraphState:
    run_id = state.get("run_id", "unknown")
    await bus.publish(make_event(run_id, "synthesize", "started", agent="synthesizer"))

    topic = state.get("topic", "")
    notes = state.get("notes", [])
    model = settings.GROQ_MODEL  # Get from settings instead of state
    provider = settings.SEARCH_PROVIDER  # Get from settings instead of state

    report_md = _mk_report(topic, notes, model, provider)

    await bus.publish(make_event(run_id, "synthesize", "completed", agent="synthesizer"))
    return {**state, "report_md": report_md}