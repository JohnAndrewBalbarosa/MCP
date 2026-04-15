from __future__ import annotations

import os
from pathlib import Path


def _trace_root() -> Path | None:
    raw = os.environ.get("MCP_TRACE_EXPORT_DIR", "").strip()
    if not raw:
        return None
    return Path(raw)


def write_text(relative_path: str, content: str) -> None:
    root = _trace_root()
    if root is None:
        return

    target = root / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    normalized = content.rstrip("\n")
    target.write_text(f"{normalized}\n" if normalized else "", encoding="utf-8")