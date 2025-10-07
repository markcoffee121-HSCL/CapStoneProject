from __future__ import annotations
import os
from pathlib import Path

ARTIFACTS_DIR = Path(__file__).resolve().parents[2] / "artifacts"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

def ensure_run_dir(run_id: str) -> Path:
    d = ARTIFACTS_DIR / run_id
    d.mkdir(parents=True, exist_ok=True)
    return d

def write_text(run_id: str, filename: str, content: str) -> str:
    d = ensure_run_dir(run_id)
    p = d / filename
    p.write_text(content, encoding="utf-8")
    return str(p)

def read_text(run_id: str, filename: str) -> str | None:
    p = ARTIFACTS_DIR / run_id / filename
    if not p.exists():
        return None
    return p.read_text(encoding="utf-8")
