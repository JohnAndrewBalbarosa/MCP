from __future__ import annotations

import ast
from pathlib import Path


def _validate_bounds(total_lines: int, start_line: int, end_line: int) -> None:
    if start_line < 1:
        raise ValueError("start_line must be >= 1")
    if end_line < start_line:
        raise ValueError("end_line must be >= start_line")
    if end_line > total_lines:
        raise ValueError("end_line exceeds file length")


def read_bounded_snippet(file_path: str, start_line: int, end_line: int) -> str:
    source = Path(file_path)
    lines = source.read_text(encoding="utf-8").splitlines(keepends=True)
    _validate_bounds(len(lines), start_line, end_line)
    return "".join(lines[start_line - 1 : end_line])


def apply_bounded_splice(file_path: str, start_line: int, end_line: int, replacement: str) -> None:
    source = Path(file_path)
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
