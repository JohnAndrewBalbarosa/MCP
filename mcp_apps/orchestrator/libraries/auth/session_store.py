from __future__ import annotations

import json
from pathlib import Path

from mcp_apps.orchestrator.libraries.types.contracts import SessionProfile


SESSION_FILE = Path(__file__).resolve().parents[2] / "session_profile.json"


def save_session_profile(profile: SessionProfile) -> None:
    SESSION_FILE.write_text(
        json.dumps(
            {
                "headers": profile.headers,
                "cookie_jar": profile.cookie_jar,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
