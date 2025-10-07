from __future__ import annotations
from typing import Annotated, Optional, Dict, Any
from langgraph.graph import add_messages
from operator import add

GraphState = dict[str, Any]

DEPTH_PRESETS: Dict[str, Dict[str, Any]] = {
    "quick":    {"max_sources": 3,  "fetch_timeout": 8,  "summary_words": 120},
    "standard": {"max_sources": 6,  "fetch_timeout": 12, "summary_words": 200},
    "deep":     {"max_sources": 10, "fetch_timeout": 18, "summary_words": 350},
}

def make_initial_state(
    run_id: str,
    topic: str,
    depth: str = "standard",
    domains: Optional[list[str]] = None,
    max_sources: Optional[int] = None,
) -> GraphState:
    """
    Build the initial state and inject depth-based limits. Caller max_sources overrides preset.
    """
    preset = DEPTH_PRESETS.get(depth, DEPTH_PRESETS["standard"])
    eff_max_sources = max_sources or preset["max_sources"]

    return {
        "run_id": run_id,
        "topic": topic,
        "depth": depth,
        "domains": domains or [],
        "max_sources": eff_max_sources,
        "limits": preset,
        "results": [],
        "docs": [],
        "notes": [],
        "report_md": "",
    }