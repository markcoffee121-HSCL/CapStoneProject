from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field

class RunRequest(BaseModel):
    topic: str = Field(..., description="Main research query/topic")
    depth: str = Field("standard", description="standard | deep | quick")
    domains: Optional[List[str]] = Field(default=None)
    max_sources: int = Field(6, ge=1, le=20)

class RunCreated(BaseModel):
    run_id: str

class RunStatus(BaseModel):
    run_id: str
    status: Literal["pending", "running", "completed", "error"]
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    error: Optional[str] = None
    topic: Optional[str] = None
    depth: Optional[str] = None


class RunEvent(BaseModel):
    event_id: str
    run_id: str
    step: str
    agent: Optional[str] = None
    status: str = Field(..., description="started | progress | completed | error")
    message: Optional[str] = None
    ts: datetime = Field(default_factory=datetime.utcnow)
    duration_ms: Optional[int] = None
    data: Optional[Dict[str, Any]] = None

class RunStatus(BaseModel):
    run_id: str
    status: Literal["pending","running","completed","error"]
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    error: Optional[str] = None
    topic: Optional[str] = None
    depth: Optional[str] = None