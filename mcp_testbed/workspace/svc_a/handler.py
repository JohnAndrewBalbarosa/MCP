from __future__ import annotations

from dataclasses import dataclass

SERVICE_NAME = "svc_a"
DEFAULT_THRESHOLD = 2


@dataclass(frozen=True)
class HandlerReport:
    service: str
    accepted: bool
    score: int
    note: str


def score_message(message: str) -> int:
    return sum(1 for char in message if char.isalpha())


def is_ready(message: str, threshold: int = DEFAULT_THRESHOLD) -> bool:
    return score_message(message) >= threshold


def handle_request(message: str) -> HandlerReport:
    normalized = message.strip()
    score = score_message(normalized)
    accepted = score >= DEFAULT_THRESHOLD
    note = f"{SERVICE_NAME}:{'ready' if accepted else 'blocked'}:{normalized or 'empty'}"
    return HandlerReport(service=SERVICE_NAME, accepted=accepted, score=score, note=note)


def render_status(message: str) -> str:
    report = handle_request(message)
    state = "ready" if report.accepted else "blocked"
    return f"{report.service}:{state}:{report.score}"
