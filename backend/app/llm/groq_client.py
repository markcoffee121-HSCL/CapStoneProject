from __future__ import annotations
import asyncio
from typing import List, Tuple
from groq import Groq
from ..config import settings

_client: Groq | None = None

def _get_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=settings.GROQ_API_KEY)
    return _client

async def chat(
    messages: List[dict],
    *,
    model: str | None = None,
    temperature: float = 0.2,
    max_tokens: int = 900,
) -> Tuple[str, int, int]:
    """
    Returns (text, prompt_tokens, completion_tokens)
    """
    client = _get_client()

    def _call():
        return client.chat.completions.create(
            model=model or settings.GROQ_MODEL,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    resp = await asyncio.to_thread(_call)
    text = resp.choices[0].message.content or ""
    usage = getattr(resp, "usage", None)
    prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
    completion_tokens = getattr(usage, "completion_tokens", 0) or 0
    return text, prompt_tokens, completion_tokens
