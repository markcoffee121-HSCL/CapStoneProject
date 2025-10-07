from __future__ import annotations
import asyncio
from datetime import datetime
from ..observability.events import bus, make_event
from ..config import settings
from ..graph.state import GraphState
from ..storage.files import write_text
from ..integration.n8n import notify_n8n

def _delay() -> float:
    return (getattr(settings, "SIM_DELAY_MS", 600) / 1000)

async def presenter_node(state: GraphState) -> GraphState:
    run_id = state.get("run_id", "unknown")
    await bus.publish(make_event(run_id, "present", "started", agent="presenter"))

    md = state.get("report_md", "# Empty Report\n")
    path = write_text(run_id, "report.md", md)

    await asyncio.sleep(_delay())
    await bus.publish(make_event(run_id, "present", "completed", agent="presenter", data={"path": path}))

    payload = {
        "run_id": run_id,
        "topic": state.get("topic"),
        "depth": state.get("depth"),
        "plan": state.get("plan", []),
        "sources": [d["url"] for d in state.get("docs", []) if d.get("url")],
        "report_md": md,
        "critique": state.get("critique"),
        "artifact_path": path,
        "model": settings.GROQ_MODEL,
        "search_provider": settings.SEARCH_PROVIDER,
        "ts": datetime.utcnow().isoformat(),
    }

    await bus.publish(make_event(run_id, "notify", "started", agent="n8n", message="Sending to n8n webhook"))
    result = await notify_n8n(payload)
    if result is None:
        await bus.publish(make_event(run_id, "notify", "completed", agent="n8n", message="N8N_WEBHOOK_URL not set", data={"skipped": True}))
    else:
        status, text = result
        status_label = "completed" if 200 <= status < 300 else "error"
        info = {"status": status}
        if status == 0:
            info["error"] = text
        elif status >= 300:
            info["response"] = (text[:240] + "…") if len(text) > 240 else text
        await bus.publish(make_event(run_id, "notify", status_label, agent="n8n", data=info))

    return {**state, "artifacts": {"report_md": path}}
