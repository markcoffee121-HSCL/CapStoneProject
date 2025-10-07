from __future__ import annotations
import asyncio, hmac, hashlib, json
from typing import Any, Dict, Tuple, Optional
import httpx
from ..config import settings
from ..observability.metrics import record_webhook_error, record_webhook_request

def _sign(body: bytes, secret: str) -> str:
    return "sha256=" + hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()

async def notify_n8n(payload: Dict[str, Any]) -> Optional[Tuple[int, str]]:
    """
    Returns (status_code, text) or None if N8N_WEBHOOK_URL not set.
    status=0 means connection exception.
    """
    url = (settings.N8N_WEBHOOK_URL or "").strip()
    if not url:
        return None

    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {"content-type": "application/json"}
    if getattr(settings, "N8N_SECRET", None):
        headers["X-HSCL-Signature"] = _sign(body, settings.N8N_SECRET)

    record_webhook_request("n8n")

    async with httpx.AsyncClient(timeout=20) as client:
        try:
            r = await client.post(url, content=body, headers=headers, follow_redirects=True)
            if not (200 <= r.status_code < 300):
                record_webhook_error("n8n")
            return r.status_code, r.text
        except Exception as e:
            record_webhook_error("n8n")
            return 0, repr(e)
