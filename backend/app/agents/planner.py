from __future__ import annotations
import asyncio, re
from typing import List
from ..observability.events import bus, make_event
from ..observability.metrics import record_groq_usage, record_groq_error
from ..config import settings
from ..graph.state import GraphState
from ..llm.groq_client import chat

def _delay() -> float:
    return (getattr(settings, "SIM_DELAY_MS", 600) / 1000)

def _parse_plan(text: str) -> List[str]:
    lines = []
    for line in text.splitlines():
        s = line.strip(" -\t")
        if not s:
            continue
        if re.match(r"^(\d+[\).\]]|[-*•])\s+", line.strip()):
            lines.append(re.sub(r"^(\d+[\).\]]|[-*•])\s+", "", line.strip()))
    # fallback: split by sentences if nothing matched
    if not lines:
        lines = [s.strip() for s in re.split(r"[.;]\s+", text) if s.strip()]
    # take 3–6 steps
    return lines[:6] if len(lines) > 6 else lines

async def planner_node(state: GraphState) -> GraphState:
    run_id = state.get("run_id", "unknown")
    topic = state.get("topic", "")
    await bus.publish(make_event(run_id, "plan", "started", agent="planner", message=f"Planning: {topic}"))

    plan: List[str]
    if settings.GROQ_API_KEY:
        try:
            messages = [
                {"role": "system", "content": "You are a precise research planner. Output 3–6 short, actionable steps."},
                {"role": "user", "content": f"Topic: {topic}\nDepth: {state.get('depth','standard')}\nDomains: {', '.join(state.get('domains', []))}"}
            ]
            text, pt, ct = await chat(messages, max_tokens=300, temperature=0.1)
            record_groq_usage(settings.GROQ_MODEL, "planner", pt, ct)
            plan = _parse_plan(text) or [
                "Clarify scope",
                "Collect high-quality sources",
                "Extract evidence",
                "Write a brief with citations",
            ]
        except Exception:
            record_groq_error(settings.GROQ_MODEL, "planner")
            plan = [
                "Clarify scope",
                "Collect high-quality sources",
                "Extract evidence",
                "Write a brief with citations",
            ]
    else:
        plan = [
            f"Clarify scope for: {topic}",
            "Identify 3–6 high-quality sources",
            "Extract key claims & evidence",
            "Synthesize into a brief report with citations",
        ]

    await asyncio.sleep(_delay())
    await bus.publish(make_event(run_id, "plan", "completed", agent="planner", data={"steps": len(plan)}))
    return {**state, "plan": plan}
