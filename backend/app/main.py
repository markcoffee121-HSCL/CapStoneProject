from fastapi import BackgroundTasks, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .observability.metrics import init_metrics
from .observability.logger import setup_json_logging
from .observability.events import bus, sse_endpoint, make_event
from .models import RunCreated, RunRequest
from .storage.runs import store
from .graph.state import make_initial_state
from .graph.graph import build_research_graph
from .storage.files import read_text
from .integration.n8n import notify_n8n
from datetime import datetime
from fastapi import HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from .storage.files import ARTIFACTS_DIR, read_text
import logging
import traceback

# Configure logging early
setup_json_logging()

VERSION = "0.1.0"

app = FastAPI(
    title="HSCL Capstone Research Orchestrator",
    version=VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS for dashboard/dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Expose /metrics (must be before startup)
init_metrics(app)

# Build the research graph once per process
_GRAPH = build_research_graph()


@app.get("/healthz")
def healthz():
    return {
        "status": "ok",
        "service": "hscl-capstone-backend",
        "version": VERSION,
        "groq_model": settings.GROQ_MODEL,
        "search_provider": settings.SEARCH_PROVIDER,
    }


@app.get("/")
def root():
    return {"message": "HSCL Capstone backend is running. See /healthz and /docs."}


# ---------- SSE events ----------
@app.get("/events")
async def events(request: Request, run_id: str | None = None):
    """
    Server-Sent Events stream. Keep this tab open to watch runs in real-time.
    Optional ?run_id=<uuid> to filter a specific run.
    """
    return await sse_endpoint(request, run_id=run_id)


# ---------- LangGraph runner ----------
async def _run_graph_async(run_id: str, req: RunRequest):
    try:
        store.start(run_id)

        init_state = make_initial_state(
            run_id=run_id,
            topic=req.topic,
            depth=req.depth,
            domains=req.domains,
            max_sources=req.max_sources,
        )

        # Each node publishes its own SSE step events
        await _GRAPH.ainvoke(init_state)

        store.finish(run_id)
        await bus.publish(make_event(run_id, "run", "completed", message="Run finished"))
    except Exception as e:
        # log full traceback to the backend console
        logging.exception("Run crashed (run_id=%s)", run_id)
        # keep the original exception type for easier diagnosis in UI/tests
        store.error(run_id, repr(e))
        await bus.publish(make_event(run_id, "run", "error", message=repr(e)))


# ---------- API ----------
@app.post("/research", response_model=RunCreated)
async def research(req: RunRequest, background: BackgroundTasks):
    """
    Start a research run. Returns {"run_id": "..."} immediately.
    Subscribe to /events (or /events?run_id=...) to watch progress.
    """
    rs = store.create(topic=req.topic, depth=req.depth)  # Add topic and depth here
    background.add_task(_run_graph_async, rs.run_id, req)
    return RunCreated(run_id=rs.run_id)


@app.get("/runs/{run_id}")
def get_run(run_id: str):
    rs = store.get(run_id)
    if not rs:
        return {"error": "not_found"}
    return rs

@app.get("/runs")
def list_runs():
    return store.list_all()

@app.post("/runs/{run_id}/notify")
async def resend_to_n8n(run_id: str):
    rs = store.get(run_id)
    if not rs:
        return {"ok": False, "error": "not_found"}

    report_md = read_text(run_id, "report.md") or ""
    payload = {
        "run_id": run_id,
        "topic": rs.topic if hasattr(rs, 'topic') else "unknown",  # Safely access topic
        "depth": rs.depth if hasattr(rs, 'depth') else "unknown",  # Safely access depth
        "plan": [],
        "sources": [],
        "report_md": report_md,
        "critique": None,
        "artifact_path": f"artifacts/{run_id}/report.md",
        "model": settings.GROQ_MODEL,
        "search_provider": settings.SEARCH_PROVIDER,
        "ts": datetime.utcnow().isoformat(),
    }
    res = await notify_n8n(payload)
    return {"ok": res is not None, "result": res}

@app.get("/runs/{run_id}/report")
def get_report(run_id: str, inline: bool = False):
    path = ARTIFACTS_DIR / run_id / "report.md"
    if not path.exists():
        raise HTTPException(status_code=404, detail="report_not_found")
    if inline:
        return PlainTextResponse(path.read_text(encoding="utf-8"))
    return FileResponse(
        path,
        media_type="text/markdown",
        filename=f"{run_id}-report.md",
    )
