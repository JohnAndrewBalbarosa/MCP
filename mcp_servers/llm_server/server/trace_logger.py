from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path


def _trace_root() -> Path | None:
    raw = os.environ.get("MCP_TRACE_LOG_DIR", "").strip()
    if not raw:
        return None
    return Path(raw)


def _write_entry(relative_path: str, content: str) -> None:
    root = _trace_root()
    if root is None:
        return

    target = root / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    body = content.rstrip("\n")
    with target.open("a", encoding="utf-8") as handle:
        handle.write(f"timestamp={timestamp}\n")
        handle.write(body)
        handle.write("\n\n")


def log_generation(
    role: str,
    provider_id: str,
    model: str,
    prompt: str,
    response: str,
    *,
    prompt_index: int | None = None,
    transport: str = "SDK",
    response_status: str = "OK",
    error_message: str = "",
) -> None:
    index_line = f"prompt_index={prompt_index}\n" if prompt_index is not None else ""
    error_line = f"error_message={error_message}\n" if error_message else ""
    model_entry = (
        f"role={role}\n"
        f"provider_id={provider_id}\n"
        f"model={model}\n"
        f"transport={transport}\n"
        f"response_status={response_status}\n"
        f"{index_line}"
        f"{error_line}"
        f"PROMPT:\n{prompt}\n\n"
        f"RESPONSE:\n{response}"
    )
    api_entry = (
        f"role={role}\n"
        f"provider_id={provider_id}\n"
        f"model={model}\n"
        f"transport={transport}\n"
        f"http_status=n/a\n"
        f"response_status={response_status}\n"
        f"prompt_length={len(prompt)}\n"
        f"response_length={len(response)}\n"
        f"{index_line}"
        f"{error_line}"
        f"ANSWER:\n{response}"
    )
    _write_entry(f"models/{role}.log", model_entry)
    _write_entry(f"api/{role}.log", api_entry)