from __future__ import annotations


def enforce_bounds(payload: dict) -> None:
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
