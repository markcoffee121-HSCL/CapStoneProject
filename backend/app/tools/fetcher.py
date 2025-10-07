from __future__ import annotations
import asyncio
from typing import Any, Dict, List, Optional, Tuple
import httpx
from bs4 import BeautifulSoup
import trafilatura

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    )
}

async def _download(client: httpx.AsyncClient, url: str) -> Tuple[str, Optional[str]]:
    try:
        r = await client.get(url, headers=HEADERS, follow_redirects=True)
        if r.status_code >= 400:
            return url, None
        return url, r.text
    except Exception:
        return url, None

def _clean_with_trafilatura(html: str, url: str) -> str:
    try:
        text = trafilatura.extract(
            html,
            url=url,
            include_comments=False,
            include_tables=False,
            favor_recall=True,
            no_fallback=False,
        )
        if text:
            return text.strip()
    except Exception:
        pass
    return ""

def _fallback_bs4(html: str) -> str:
    try:
        soup = BeautifulSoup(html, "lxml")
        for tag in soup(["script", "style", "noscript"]):
            tag.extract()
        text = soup.get_text(separator="\n")
        return "\n".join(line.strip() for line in text.splitlines() if line.strip())
    except Exception:
        return ""

def _title_from_html(html: str) -> str:
    try:
        soup = BeautifulSoup(html, "lxml")
        t = soup.title.string if soup.title and soup.title.string else ""
        return t.strip()
    except Exception:
        return ""

async def fetch_one(url: str, timeout: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """
    Fetch and extract a single URL. timeout is seconds; if None defaults to 20.
    """
    to = timeout or 20
    async with httpx.AsyncClient(timeout=to) as client:
        _, html = await _download(client, url)
    if not html:
        return None

    text = _clean_with_trafilatura(html, url) or _fallback_bs4(html)
    if not text:
        return None

    title = _title_from_html(html) or url
    return {"url": url, "title": title, "content": text}

async def fetch_many(
    urls: List[str],
    concurrency: int = 5,
    timeout: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Fetch a list of URLs concurrently. Respects the same timeout per request.
    """
    sem = asyncio.Semaphore(concurrency)
    out: List[Dict[str, Any]] = []

    async def _task(u: str):
        async with sem:
            doc = await fetch_one(u, timeout=timeout)
            if doc:
                out.append(doc)

    await asyncio.gather(*[_task(u) for u in urls])
    return out
