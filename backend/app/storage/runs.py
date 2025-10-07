from __future__ import annotations
import uuid
from datetime import datetime
from typing import Dict, Optional, List
from ..models import RunStatus

class RunStore:
    def __init__(self) -> None:
        self._runs: Dict[str, RunStatus] = {}

    def create(self, *, topic: str | None = None, depth: str | None = None) -> RunStatus:
        run_id = str(uuid.uuid4())
        rs = RunStatus(
        run_id=run_id, 
        status="pending", 
        created_at=datetime.utcnow(), 
        topic=topic, 
        depth=depth
    )
        self._runs[run_id] = rs
        return rs

    def start(self, run_id: str) -> None:
        rs = self._runs[run_id]
        rs.status = "running"
        rs.started_at = datetime.utcnow()

    def finish(self, run_id: str) -> None:
        rs = self._runs[run_id]
        rs.status = "completed"
        rs.finished_at = datetime.utcnow()

    def error(self, run_id: str, err: str) -> None:
        rs = self._runs[run_id]
        rs.status = "error"
        rs.error = err
        rs.finished_at = datetime.utcnow()

    def get(self, run_id: str) -> Optional[RunStatus]:
        return self._runs.get(run_id)

    def list_all(self) -> List[RunStatus]:
        return sorted(self._runs.values(), key=lambda r: r.created_at, reverse=True)
    
store = RunStore()
