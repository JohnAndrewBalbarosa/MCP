from __future__ import annotations


def enforce_bounds(payload: dict, max_span_lines: int | None = None) -> None:
    required = [
        "target_file",
        "start_line",
        "end_line",
        "mutation_intent",
    ]
    missing = [key for key in required if key not in payload]
    if missing:
        raise ValueError(f"Missing bounded payload fields: {missing}")

    if payload["start_line"] < 1:
        raise ValueError("start_line must be >= 1")
    if payload["end_line"] < payload["start_line"]:
        raise ValueError("end_line must be >= start_line")
    if max_span_lines is not None:
        span = payload["end_line"] - payload["start_line"] + 1
        if span > max_span_lines:
            raise ValueError(f"Bounded span {span} exceeds executor limit {max_span_lines}")
