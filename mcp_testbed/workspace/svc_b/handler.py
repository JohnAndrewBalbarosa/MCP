from __future__ import annotations

from dataclasses import dataclass

SERVICE_NAME = "svc_b"
DEFAULT_LIMIT = 8


@dataclass(frozen=True)
class HandlerReport:
    service: str
    truncated: bool
    message: str


def cap_message(message: str, limit: int = DEFAULT_LIMIT) -> str:
    text = message.strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def handle_request(message: str, limit: int = DEFAULT_LIMIT) -> HandlerReport:
    text = message.strip()
    capped = cap_message(text, limit)
    return HandlerReport(service=SERVICE_NAME, truncated=capped != text, message=capped)


def summarize(message: str) -> str:
    report = handle_request(message)
    state = "truncated" if report.truncated else "plain"
    return f"{report.service}:{state}:{report.message}"
