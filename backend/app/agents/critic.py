from __future__ import annotations
import asyncio
from ..observability.events import bus, make_event
from ..observability.metrics import record_groq_usage, record_groq_error
from ..config import settings
from ..graph.state import GraphState
from ..llm.groq_client import chat

def _delay() -> float:
    return (getattr(settings, "SIM_DELAY_MS", 600) / 1000)

async def critic_node(state: GraphState) -> GraphState:
    run_id = state.get("run_id", "unknown")
    await bus.publish(make_event(run_id, "critique", "started", agent="critic"))

    critique = "Check for outdated sources; add quantitative evidence if available. (stub)"

    if settings.GROQ_API_KEY:
        try:
            sys = (
                "You are a rigorous, concise reviewer. Provide 2–4 bullet critique points "
                "to strengthen the brief. Be specific and actionable."
            )
            usr = state.get("report_md", "# (empty)")
            text, pt, ct = await chat(
                [{"role": "system", "content": sys}, {"role": "user", "content": usr}],
                temperature=0.3,
                max_tokens=220,
            )
            record_groq_usage(settings.GROQ_MODEL, "critic", pt, ct)
            critique = text.strip() or critique
        except Exception:
            record_groq_error(settings.GROQ_MODEL, "critic")

    await asyncio.sleep(_delay())
    await bus.publish(make_event(run_id, "critique", "completed", agent="critic", data={"notes": 1}))
    return {**state, "critique": critique}
