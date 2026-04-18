from __future__ import annotations

import ast
import os
from pathlib import Path


def _validate_bounds(total_lines: int, start_line: int, end_line: int) -> None:
    if start_line < 1:
        raise ValueError("start_line must be >= 1")
    if end_line < start_line:
        raise ValueError("end_line must be >= start_line")
    if end_line > total_lines:
        raise ValueError("end_line exceeds file length")


def _workspace_root() -> Path:
    configured = os.environ.get("MCP_WORKSPACE_ROOT", "").strip()
    if configured:
        candidate = Path(configured).expanduser()
        if candidate.exists():
            return candidate

    fallback = Path(__file__).resolve().parents[3] / "mcp_testbed" / "workspace"
    if fallback.exists():
        return fallback

    return Path.cwd()


def _resolve_file_path(file_path: str) -> Path:
    source = Path(file_path).expanduser()
    if source.is_absolute():
        return source
    return _workspace_root() / source


def read_bounded_snippet(file_path: str, start_line: int, end_line: int) -> str:
    source = _resolve_file_path(file_path)
    if not source.exists():
        # New file: executor will generate the full content from scratch
        return ""
    lines = source.read_text(encoding="utf-8").splitlines(keepends=True)
    _validate_bounds(len(lines), start_line, end_line)
    return "".join(lines[start_line - 1 : end_line])


def apply_bounded_splice(file_path: str, start_line: int, end_line: int, replacement: str) -> None:
    source = _resolve_file_path(file_path)

    if not source.exists():
        # New file: create parent directories and write the replacement directly.
        # Line bounds are irrelevant here — the executor generated the full content.
        source.parent.mkdir(parents=True, exist_ok=True)
        if source.suffix == ".py":
            ast.parse(replacement)  # fail fast on syntax corruption
        source.write_text(replacement, encoding="utf-8")
        return

    lines = source.read_text(encoding="utf-8").splitlines(keepends=True)
    _validate_bounds(len(lines), start_line, end_line)

    before = lines[: start_line - 1]
    after = lines[end_line:]
    replacement_lines = replacement.splitlines(keepends=True)
    merged = before + replacement_lines + after

    candidate = "".join(merged)
    if source.suffix == ".py":
        ast.parse(candidate)

    temp_path = source.with_suffix(source.suffix + ".tmp")
    temp_path.write_text(candidate, encoding="utf-8")
    temp_path.replace(source)
