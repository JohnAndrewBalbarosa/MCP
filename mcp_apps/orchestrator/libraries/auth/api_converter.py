from __future__ import annotations


def convert_ui_request_to_rest(captured_request: dict) -> dict:
    """Maps captured browser request shape to a browserless REST call contract."""
    return {
        "url": captured_request.get("url"),
        "headers": captured_request.get("headers", {}),
        "body_template": captured_request.get("body", {}),
        "method": captured_request.get("method", "POST"),
    }
