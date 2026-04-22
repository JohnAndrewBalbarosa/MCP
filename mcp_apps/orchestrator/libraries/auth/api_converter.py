from __future__ import annotations

from typing import Dict


def sanitize_headers(headers: Dict[str, str] | None) -> Dict[str, str]:
    raw_headers = headers or {}
    sanitized: Dict[str, str] = {}
    transient = {
        "content-length",
        "host",
        "connection",
    }
    for key, value in raw_headers.items():
        normalized_key = str(key).strip()
        if not normalized_key:
            continue
        if normalized_key.lower() in transient:
            continue
        sanitized[normalized_key] = str(value)
    return sanitized


def normalize_api_request(raw_request: dict) -> dict:
    return {
        "url": raw_request.get("url"),
        "headers": sanitize_headers(raw_request.get("headers")),
        "query_params": dict(raw_request.get("query_params", {}) or {}),
        "body_template": raw_request.get("body") or raw_request.get("body_template") or {},
        "method": str(raw_request.get("method", "POST")).upper(),
    }


def normalize_session_profile(raw_session: dict) -> dict:
    return {
        "headers": sanitize_headers(raw_session.get("headers")),
        "cookie_jar": dict(raw_session.get("cookie_jar", {}) or raw_session.get("cookies", {}) or {}),
        "tokens": dict(raw_session.get("tokens", {}) or {}),
        "expires_at": raw_session.get("expires_at"),
    }


def convert_ui_request_to_rest(captured_request: dict) -> dict:
    """Compatibility alias kept for older call sites."""
    return normalize_api_request(captured_request)
