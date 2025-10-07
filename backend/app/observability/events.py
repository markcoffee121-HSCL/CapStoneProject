from __future__ import annotations
import asyncio, json, uuid
from datetime import datetime
from typing import AsyncIterator, Dict, Optional
from fastapi import Request
from starlette.responses import StreamingResponse
from ..models import RunEvent

def _format_sse(data: str, event: Optional[str] = None, id: Optional[str] = None) -> str:
    lines = []
    if event: lines.append(f"event: {event}")
    if id: lines.append(f"id: {id}")
    for chunk in data.splitlines():
        lines.append(f"data: {chunk}")
    lines.append("")
    return "\n".join(lines)

class EventBus:
    def __init__(self) -> None:
        self._subscribers: Dict[int, asyncio.Queue] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        async with self._lock:
            self._subscribers[id(q)] = q
        return q

    async def unsubscribe(self, q: asyncio.Queue) -> None:
        async with self._lock:
            self._subscribers.pop(id(q), None)

    async def publish(self, event: RunEvent) -> None:
        async with self._lock:
            subs = list(self._subscribers.values())
        for q in subs:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass

bus = EventBus()

async def sse_endpoint(request: Request, run_id: Optional[str] = None) -> StreamingResponse:
    q = await bus.subscribe()

    async def event_stream() -> AsyncIterator[bytes]:
        try:
            hello = {"ts": datetime.utcnow().isoformat(), "message": "connected"}
            yield _format_sse(json.dumps(hello), event="hello").encode("utf-8")

            while True:
                if await request.is_disconnected():
                    break
                try:
                    event: RunEvent = await asyncio.wait_for(q.get(), timeout=15)
                except asyncio.TimeoutError:
                    yield b": keep-alive\n\n"
                    continue
                if run_id and event.run_id != run_id:
                    continue
                payload = event.model_dump(mode='json')
                msg = _format_sse(json.dumps(payload), event="run_event", id=event.event_id)
                yield msg.encode("utf-8")
        finally:
            await bus.unsubscribe(q)

    return StreamingResponse(event_stream(), media_type="text/event-stream")

def make_event(run_id: str, step: str, status: str,
               agent: Optional[str] = None, message: Optional[str] = None,
               duration_ms: Optional[int] = None, data: Optional[dict] = None) -> RunEvent:
    return RunEvent(
        event_id=str(uuid.uuid4()),
        run_id=run_id,
        step=step,
        agent=agent,
        status=status,
        message=message,
        duration_ms=duration_ms,
        data=data,
    )
